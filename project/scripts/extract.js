// استخراج سند ۳۲ صفحه‌ای از آرشیو چندجلدی CamScanner (RAR5).
//
// اجرا:
//   node project/scripts/extract.js [مسیر part1.rar] [پوشهٔ مقصد]
//
// نکته: این دو فایل، دو جلدِ یک مجموعهٔ RAR5 هستند؛ استخراج فقط از part1 آغاز می‌شود
// و کتابخانه خودکار جلد دوم را دنبال می‌کند. هرگز فایل‌ها را concatenate نکنید.
const { createExtractorFromFile } = require('node-unrar-js');
const path = require('path');
const fs = require('fs');

const REPO = path.resolve(__dirname, '..', '..');
const src = process.argv[2]
  || path.join(REPO, 'CamScanner 10-17-26 20.43.part1.rar');
const target = process.argv[3]
  || path.join(__dirname, '..', 'source', 'extracted');

(async () => {
  if (!fs.existsSync(src)) {
    console.error('آرشیو یافت نشد:', src);
    process.exit(1);
  }
  fs.mkdirSync(target, { recursive: true });
  const extractor = await createExtractorFromFile({ filepath: src, targetPath: target });
  const list = extractor.getFileList();
  for (const fh of list.fileHeaders) {
    console.log('در آرشیو:', fh.name, fh.unpSize, 'بایت');
  }
  const extracted = extractor.extract();
  for (const f of extracted.files) {
    console.log('استخراج شد:', f.fileHeader.name);
  }
  console.log('مقصد:', target);
})().catch(e => { console.error('خطا:', e); process.exit(1); });
