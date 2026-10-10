// index.html 안의 <script> 블록을 꺼내 문법만 검사한다 (실행하지 않음).
// Node가 따로 없어서 VS Code에 들어 있는 Electron을 Node처럼 돌려 쓴다:
//   ELECTRON_RUN_AS_NODE=1 "<VS Code 경로>/Code.exe" tools/check_html_js.js
const fs = require('fs'), path = require('path'), vm = require('vm');
const file = process.argv[2] || path.join(__dirname, '..', 'index.html');
const html = fs.readFileSync(file, 'utf8');
const re = /<script>([\s\S]*?)<\/script>/g;
let m, n = 0, bad = 0;
while((m = re.exec(html))){
  n++;
  const line = html.slice(0, m.index).split('\n').length;
  try{ new vm.Script(m[1], { filename: 'script#'+n+' (index.html '+line+'행부터)' }); }
  catch(e){ bad++; console.log('문법 오류:', e.message, '\n', (e.stack||'').split('\n').slice(0,3).join('\n')); }
}
console.log('스크립트 '+n+'개 검사, 오류 '+bad+'개');
process.exit(bad ? 1 : 0);
