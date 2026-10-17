const { createExtractorFromFile } = require('node-unrar-js');
const path = require('path');
const fs = require('fs');

(async () => {
  const src = '/home/user/gozarshkar/CamScanner 10-17-26 20.43.part1.rar';
  const target = '/home/user/project/source/extracted';
  fs.mkdirSync(target, { recursive: true });
  const extractor = await createExtractorFromFile({ filepath: src, targetPath: target });
  const list = extractor.getFileList();
  console.log('arcHeader:', JSON.stringify(list.arcHeader));
  for (const fh of list.fileHeaders) {
    console.log(JSON.stringify(fh));
  }
  const extracted = extractor.extract();
  for (const f of extracted.files) {
    console.log('extracted:', f.fileHeader.name);
  }
})().catch(e => { console.error('ERR', e); process.exit(1); });
