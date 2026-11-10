/**
 * Teacher Resilience · Thursday 12 November — Breakout Action Board
 * Backend for the "Breakout Lab" tab of the Teacher Well-being Explorer (Shinylive app),
 * plus an optional Google Form that feeds the same Sheet.
 *
 * Running setup() once creates:
 *   1. A bilingual (EN / Bahasa Indonesia) Google Form: one submission per breakout room
 *   2. A linked Google Sheet with:
 *        - "Board": live view sorted by WHO needs to act (Me → Team → School leader → Dinas),
 *          with counts per category and colour coding
 *        - "Responses": raw form responses
 *        - "Links": form links to paste into your Google Site / Zoom chat
 *
 * HOW TO RUN
 *   1. script.google.com → New project → paste this file → Save → choose "setup" → Run
 *      → approve permissions. The Logs (and the "Links" tab of the new Sheet) show the URLs.
 *   2. Deploy → New deployment → type "Web app" → Execute as: Me · Who has access: Anyone
 *      → Deploy → copy the Web app URL (ends in /exec).
 *   3. Paste that URL into BOARD_URL at the top of app/breakout.py and rebuild the app.
 *
 * The app reads and writes through doGet() below. Posts are upserted by room number, so
 * a room that re-posts replaces its earlier row. Form submissions land in the same Sheet.
 *
 * After a test run, use clearTestResponses() to empty the Form and Sheet before Thursday.
 */

const TITLE = 'Thursday Action Board · Papan Aksi Kamis';
const ROOMS = 8; // number of breakout rooms offered in the dropdown
const BOARD_CODE = 'brite12'; // must match BOARD_CODE in app/breakout.py

const LEVELS = ['SD', 'SMP', 'Both · Keduanya'];

const ISSUES = [
  // Issues from the 9 November chat
  'After-hours parent messages · Pesan orang tua di luar jam kerja',
  'Repeated forms, reporting, Dapodik, routine meetings · Formulir & laporan berulang, Dapodik, rapat rutin',
  'Events, extracurriculars, homeroom duties · Kepanitiaan acara, ekstrakurikuler & tugas wali kelas',
  'Setting limits when leadership support feels weak · Menetapkan batas saat dukungan pimpinan terasa lemah',
  'Teaching while stressed, pressure to look perfect · Mengajar saat stres & tekanan untuk terlihat sempurna',
  'Burnout signs and what to do · Tanda burnout & apa yang dilakukan',
  'Supporting others without taking on everything · Mendukung siswa & rekan tanpa menanggung semuanya',
  'Large classes, noticing student stress · Kelas besar & mengenali stres siswa',
  'Growth mindset, learning from peers · Pola pikir bertumbuh & belajar dari rekan',
  'Protecting health, family, priorities · Menjaga kesehatan, keluarga & prioritas lain',
  // Fictional cases
  'Case E1 · SD · Bu Rina',
  'Case E2 · SD · Pak Budi',
  'Case E3 · SD · Bu Maya',
  'Case J1 · SMP · Pak Andi',
  'Case J2 · SMP · Bu Sari',
  'Case J3 · SMP · Pak Hendra'
];

const THEMES = [
  'B · Building resilience · Membangun resiliensi',
  'R · Relationships · Relasi',
  'i · Wellbeing · Kesejahteraan',
  'T · Taking initiative · Mengambil inisiatif',
  'E · Emotions · Emosi'
];

// The numeric prefixes make the Board sort in this order.
const WHO = [
  '1 · Me · Saya sendiri',
  '2 · Our team, KKG or MGMP · Tim kami, KKG atau MGMP',
  '3 · School leader · Kepala sekolah',
  '4 · Dinas or beyond school · Dinas atau di luar sekolah'
];

const WHO_COLOURS = ['#d9ead3', '#cfe2f3', '#fff2cc', '#e6d7f0'];

function setup() {
  // ---------- 1. FORM ----------
  const form = FormApp.create(TITLE);
  form
    .setDescription(
      'One submission per breakout room. English or Bahasa Indonesia welcome.\n' +
      'Please do not include names, school names, student details, or personal stories.\n\n' +
      'Satu kiriman per ruang. Boleh menulis dalam bahasa Inggris atau Bahasa Indonesia.\n' +
      'Mohon jangan mencantumkan nama, nama sekolah, data siswa, atau cerita pribadi.'
    )
    .setCollectEmail(false)
    .setAllowResponseEdits(true)
    .setShowLinkToRespondAgain(false)
    .setConfirmationMessage(
      "Thank you! Your room's action is on the board.\nTerima kasih! Aksi ruang Anda sudah masuk ke papan."
    );
  // Lets participants outside your Google Workspace domain respond (ignored on personal accounts).
  try { form.setRequireLogin(false); } catch (e) {}
  // Newer Forms require publishing; harmless if unsupported.
  try { if (typeof form.setPublished === 'function') form.setPublished(true); } catch (e) {}

  form.addListItem()
    .setTitle('Breakout room number · Nomor ruang')
    .setChoiceValues(Array.from({ length: ROOMS }, (_, i) => String(i + 1)))
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Level · Jenjang')
    .setChoiceValues(LEVELS)
    .setRequired(true);

  form.addListItem()
    .setTitle('Issue or case · Isu atau kasus')
    .setHelpText('The issue or fictional case your room was given · Isu atau kasus yang diberikan ke ruang Anda')
    .setChoiceValues(ISSUES)
    .setRequired(true);

  const themeItem = form.addCheckboxItem()
    .setTitle('BRiTE theme · Tema BRiTE')
    .setHelpText('Choose one or two · Pilih satu atau dua')
    .setChoiceValues(THEMES)
    .setRequired(true);
  themeItem.setValidation(FormApp.createCheckboxValidation().requireSelectAtMost(2).build());

  form.addParagraphTextItem()
    .setTitle('One action we can try · Satu tindakan yang bisa kami coba')
    .setRequired(true);

  form.addParagraphTextItem()
    .setTitle('Support we need, and who can provide it · Dukungan yang kami butuhkan, dan siapa yang bisa memberikannya');

  form.addMultipleChoiceItem()
    .setTitle('Who mainly needs to act? · Siapa yang terutama perlu bertindak?')
    .setChoiceValues(WHO)
    .setRequired(true);

  form.addTextItem()
    .setTitle("What we'll check in one week · Apa yang akan kami periksa dalam satu minggu")
    .setRequired(true);

  // ---------- 2. SHEET ----------
  const created = SpreadsheetApp.create(TITLE + ' — Responses');
  created.setSpreadsheetLocale('en_US'); // keeps formula separators predictable
  form.setDestination(FormApp.DestinationType.SPREADSHEET, created.getId());
  SpreadsheetApp.flush();

  const ss = SpreadsheetApp.openById(created.getId());
  let resp = null;
  for (let i = 0; i < 10 && !resp; i++) {
    resp = ss.getSheets().find(s => s.getFormUrl());
    if (!resp) { Utilities.sleep(1000); SpreadsheetApp.flush(); }
  }
  if (!resp) resp = ss.getSheets().find(s => s.getName().indexOf('Form') === 0);
  resp.setName('Responses');
  resp.getRange(1, 10).setValue('Source');
  ss.getSheets().forEach(s => { if (s.getSheetId() !== resp.getSheetId()) ss.deleteSheet(s); });

  // Response columns: A Timestamp, B Room, C Level, D Issue, E Theme, F Action, G Support, H Who, I Check
  const board = ss.insertSheet('Board', 0);

  board.getRange('A1')
    .setValue('Who can make each change? · Siapa yang bisa membuat perubahan ini?')
    .setFontSize(14).setFontWeight('bold');

  board.getRange('A3:B3').setValues([['Who needs to act · Siapa yang bertindak', 'Rooms · Ruang']])
    .setFontWeight('bold');
  WHO.forEach((w, i) => {
    const r = 4 + i;
    board.getRange(r, 1).setValue(w).setBackground(WHO_COLOURS[i]);
    board.getRange(r, 2).setFormula(`=COUNTIF(Responses!H2:H,A${r})`).setHorizontalAlignment('center');
  });

  const HEADER_ROW = 9;
  board.getRange(HEADER_ROW, 1, 1, 8).setValues([[
    'Who needs to act · Siapa',
    'Room · Ruang',
    'Level · Jenjang',
    'Issue or case · Isu/kasus',
    'BRiTE',
    'Action we can try · Tindakan',
    'Support needed · Dukungan',
    'One-week check · Cek satu minggu'
  ]]).setFontWeight('bold').setBackground('#434343').setFontColor('#ffffff').setWrap(true);

  board.getRange(HEADER_ROW + 1, 1).setFormula(
    '=IFERROR(SORT(FILTER({Responses!H2:H,Responses!B2:B,Responses!C2:C,Responses!D2:D,' +
    'Responses!E2:E,Responses!F2:F,Responses!G2:G,Responses!I2:I},Responses!B2:B<>""),1,TRUE,2,TRUE),' +
    '"Waiting for the first room… · Menunggu ruang pertama…")'
  );

  const widths = [200, 60, 80, 230, 170, 300, 230, 200];
  widths.forEach((w, i) => board.setColumnWidth(i + 1, w));
  const body = board.getRange(HEADER_ROW + 1, 1, 200, 8);
  body.setWrap(true).setVerticalAlignment('top');

  const rules = WHO.map((w, i) =>
    SpreadsheetApp.newConditionalFormatRule()
      .whenFormulaSatisfied(`=LEFT($A${HEADER_ROW + 1},1)="${i + 1}"`)
      .setBackground(WHO_COLOURS[i])
      .setRanges([body])
      .build()
  );
  board.setConditionalFormatRules(rules);
  board.setHiddenGridlines(true);

  // ---------- 3. LINKS ----------
  const publicUrl = form.getPublishedUrl();
  let shortUrl = '';
  try { shortUrl = form.shortenFormUrl(publicUrl); } catch (e) {}

  const links = ss.insertSheet('Links');
  links.getRange(1, 1, 5, 2).setValues([
    ['Form link for rooms (paste in Zoom chat / Site)', publicUrl],
    ['Short link', shortUrl],
    ['Form editor', form.getEditUrl()],
    ['This spreadsheet', ss.getUrl()],
    ['Board tab (screen-share this live)', ss.getUrl() + '#gid=' + board.getSheetId()]
  ]);
  links.setColumnWidth(1, 320).setColumnWidth(2, 520);
  links.getRange('A1:A5').setFontWeight('bold');

  PropertiesService.getScriptProperties().setProperties({ FORM_ID: form.getId(), SS_ID: ss.getId() });

  ss.setActiveSheet(board);
  Logger.log('Form (share): ' + publicUrl);
  Logger.log('Short link:   ' + shortUrl);
  Logger.log('Form editor:  ' + form.getEditUrl());
  Logger.log('Spreadsheet:  ' + ss.getUrl());
}

/** Deletes all test submissions from the Form and the Responses tab. Run before Thursday. */
function clearTestResponses() {
  const p = PropertiesService.getScriptProperties();
  const form = FormApp.openById(p.getProperty('FORM_ID'));
  form.deleteAllResponses();
  const resp = SpreadsheetApp.openById(p.getProperty('SS_ID')).getSheetByName('Responses');
  if (resp.getLastRow() > 1) resp.deleteRows(2, resp.getLastRow() - 1);
  Logger.log('Cleared.');
}


/**
 * JSON endpoint for the Shinylive app.
 *   ?code=brite12&op=list                    → { ok, rows: [ {room, level, issue, themes, action, support, who, check} ] }
 *   ?code=brite12&op=add&room=..&level=..&issue=..&themes=..&action_text=..&support=..&who=..&check=..
 *                                            → { ok, updated }
 */
function doGet(e) {
  const p = (e && e.parameter) || {};
  if (p.code !== BOARD_CODE) return json_({ ok: false, error: 'wrong session code' });

  const ssId = PropertiesService.getScriptProperties().getProperty('SS_ID');
  if (!ssId) return json_({ ok: false, error: 'run setup() first' });
  const sh = SpreadsheetApp.openById(ssId).getSheetByName('Responses');

  if (p.op === 'add') {
    const room = String(p.room || '').trim();
    if (!/^\d{1,2}$/.test(room)) return json_({ ok: false, error: 'room must be a number' });
    if (!p.action_text || !p.who) return json_({ ok: false, error: 'missing action or who' });
    const row = [
      new Date(), Number(room), clean_(p.level, 40), clean_(p.issue, 200), clean_(p.themes, 300),
      clean_(p.action_text, 600), clean_(p.support, 400), clean_(p.who, 100), clean_(p.check, 300), 'app'
    ];
    const lock = LockService.getScriptLock();
    lock.waitLock(15000);
    try {
      const last = sh.getLastRow();
      let target = 0;
      if (last > 1) {
        const rooms = sh.getRange(2, 2, last - 1, 1).getValues();
        for (let i = rooms.length - 1; i >= 0; i--) {
          if (String(rooms[i][0]) === room) { target = i + 2; break; }
        }
      }
      if (target) sh.getRange(target, 1, 1, row.length).setValues([row]);
      else sh.appendRow(row);
      return json_({ ok: true, updated: !!target });
    } finally {
      lock.releaseLock();
    }
  }

  const last = sh.getLastRow();
  const vals = last > 1 ? sh.getRange(2, 1, last - 1, 9).getValues() : [];
  const rows = vals
    .filter(r => r[1] !== '' && r[1] !== null)
    .map(r => ({ room: r[1], level: r[2], issue: r[3], themes: r[4], action: r[5], support: r[6], who: r[7], check: r[8] }));
  return json_({ ok: true, rows: rows });
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

// Trim, cap length, and stop text that starts with = + - @ from being read as a spreadsheet formula.
function clean_(v, max) {
  let s = String(v == null ? '' : v).trim().slice(0, max);
  if (/^[=+\-@]/.test(s)) s = "'" + s;
  return s;
}
