#!/usr/bin/env node
/**
 * 产品界面截图抓取器 —— 产品 UI 优先
 *
 * 用法：
 *   npm install                    # 首次运行，装 playwright-core
 *   node shot_capture.js config.json
 *
 * 若 playwright-core 装在别处，用 NODE_PATH 指过去：
 *   NODE_PATH="/path/to/node_modules" node shot_capture.js config.json
 *
 * config.json:
 * {
 *   "out": "spec/shots",
 *   "targets": [
 *     { "name":"01_首页", "url":"https://product.com/", "mode":"page",
 *       "fullPage":false, "wait":5000 },
 *     { "name":"02_功能页", "url":"https://help.product.com/docs/x", "mode":"imgs",
 *       "minW":640, "minH":340, "max":4, "wait":4000 }
 *   ]
 * }
 *
 * 两种模式：
 *   page —— 渲染整个网页后截图（用于官网/公开 Demo/Playground，2x 高清）
 *   imgs —— 从页面里提取真实产品界面图并原图下载（用于官方帮助文档/官网功能页，
 *           原生分辨率远高于页面截图，且天然是「功能界面」而非资讯页）
 */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

/**
 * 定位浏览器可执行文件：环境变量 CHROME_PATH > ms-playwright 缓存扫描 > 系统 Chrome/Edge > 交给 playwright 自带
 * 换机器/换 playwright 版本都不用改脚本。
 */
function findBrowser() {
  if (process.env.CHROME_PATH && fs.existsSync(process.env.CHROME_PATH)) return process.env.CHROME_PATH;

  const roots = [];
  if (process.platform === 'win32') {
    if (process.env.LOCALAPPDATA) roots.push(path.join(process.env.LOCALAPPDATA, 'ms-playwright'));
    roots.push('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe');
    roots.push('C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe');
    roots.push('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe');
  } else if (process.platform === 'darwin') {
    roots.push(path.join(process.env.HOME || '', 'Library/Caches/ms-playwright'));
    roots.push('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome');
  } else {
    roots.push(path.join(process.env.HOME || '', '.cache/ms-playwright'));
    roots.push('/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser');
  }

  for (const r of roots) {
    if (!fs.existsSync(r)) continue;
    if (fs.statSync(r).isFile()) return r;                 // 直接就是 exe
    // ms-playwright 目录：按版本号倒序找 chrome-win64/chrome.exe 等
    const dirs = fs.readdirSync(r)
      .filter(d => d.startsWith('chromium'))
      .sort().reverse();
    for (const d of dirs) {
      for (const rel of ['chrome-win64/chrome.exe', 'chrome-win/chrome.exe',
                         'chrome-mac/Chromium.app/Contents/MacOS/Chromium',
                         'chrome-linux64/chrome', 'chrome-linux/chrome']) {
        const p = path.join(r, d, rel);
        if (fs.existsSync(p)) return p;
      }
    }
  }
  return '';   // 空 → playwright-core 用内置/默认解析
}

const EXE = findBrowser();
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36';

const cfgPath = process.argv[2];
if (!cfgPath) { console.error('用法: node shot_capture.js config.json'); process.exit(1); }
const CFG = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
const OUT = path.resolve(path.dirname(cfgPath), CFG.out || 'shots');
fs.mkdirSync(OUT, { recursive: true });

const COOKIE_SEL = [
  '#cookie-banner', '.cookie-banner', '.cookie-consent', '#onetrust-banner-sdk',
  '.cc-window', '[class*="cookie"][class*="consent"]', '[id*="cookie"][id*="consent"]',
  '.gdpr', '#gdpr-banner'
];

const BAD_SRC = /logo|icon|sprite|avatar|favicon|qrcode|qr-code|placeholder|loading|spinner|emoji|badge|arrow|wave|noise|pattern|advert|banner-ad/i;

async function settle(page, wait, clean = true) {
  // 懒加载：分步滚动到底再回顶
  await page.evaluate(async () => {
    const step = window.innerHeight * 0.85;
    for (let y = 0; y < document.body.scrollHeight; y += step) {
      window.scrollTo(0, y);
      await new Promise(r => setTimeout(r, 120));
    }
    window.scrollTo(0, 0);
  }).catch(() => {});
  await page.waitForTimeout(wait || 3000);
  // 关 cookie 横幅
  for (const s of COOKIE_SEL) {
    const el = await page.$(s).catch(() => null);
    if (el) { await el.evaluate(n => n.remove()).catch(() => {}); }
  }
  if (!clean) return;   // imgs 模式只做懒加载，不动 DOM
  // 关登录/扫码弹窗（免登录页常见拦截）
  await page.keyboard.press('Escape').catch(() => {});
  await page.evaluate(() => {
    const sel = ['[class*="login"][class*="modal"]','[class*="login"][class*="dialog"]',
                 '[class*="login"][class*="popup"]','[class*="qrcode"]','[class*="scan-login"]',
                 '[class*="mask"][class*="login"]','.ant-modal-mask','.login-mask'];
    sel.forEach(s => document.querySelectorAll(s).forEach(n => {
      const r = n.getBoundingClientRect();
      if (r.width > 200 && r.height > 200) n.remove(); else if (r.width > 600) n.remove();
    }));
    // 关掉带关闭按钮的居中弹窗
    document.querySelectorAll('[class*="modal"],[class*="dialog"]').forEach(n => {
      const r = n.getBoundingClientRect();
      if (r.width > 320 && r.height > 260 && r.top < window.innerHeight * 0.6) {
        const btn = n.querySelector('[class*="close"],[aria-label*="close"],[aria-label*="关闭"]');
        if (btn) btn.click(); else n.remove();
      }
    });
    document.querySelectorAll('[class*="overlay"],[class*="backdrop"]').forEach(n => {
      const st = getComputedStyle(n);
      if (st.position === 'fixed' && parseFloat(st.zIndex || 0) > 100 && n.getBoundingClientRect().width > 600) n.remove();
    });
  }).catch(() => {});
  await page.waitForTimeout(700);

  // 点击「接受/同意」
  await page.evaluate(() => {
    const kw = /^(接受|同意|允许|我知道了|知道了|Accept|Agree|OK|Got it)$/i;
    document.querySelectorAll('button,a,[role="button"]').forEach(b => {
      const t = (b.textContent || '').trim();
      if (kw.test(t) && b.offsetParent) b.click();
    });
  }).catch(() => {});
  await page.waitForTimeout(600);
}

async function shootPage(ctx, t) {
  const page = await ctx.newPage();
  const vw = t.viewport || [1440, 900];
  await page.setViewportSize({ width: vw[0], height: vw[1] });
  await page.goto(t.url, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await settle(page, t.wait);
  const file = path.join(OUT, t.name + '.png');
  if (t.selector) {
    const el = await page.$(t.selector);
    if (!el) throw new Error('selector 未找到: ' + t.selector);
    await el.scrollIntoViewIfNeeded();
    await page.waitForTimeout(800);
    await el.screenshot({ path: file, animations: 'disabled' });
  } else {
    await page.screenshot({ path: file, fullPage: !!t.fullPage, animations: 'disabled' });
  }
  await page.close();
  return file;
}

async function shootImgs(ctx, t) {
  const page = await ctx.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(t.url, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await settle(page, t.wait, false);

  const minW = t.minW || 640, minH = t.minH || 340, max = t.max || 4;
  const cands = await page.evaluate(({ minW, minH }) => {
    const abs = u => { try { return new URL(u, location.href).href; } catch { return ''; } };
    const out = [];
    const push = (src, w, h, alt, rw) => {
      src = abs(src);
      if (!src || src.startsWith('data:')) return;
      if (w < minW || h < minH) return;
      const ar = w / h;
      if (ar < 1.05 || ar > 4.2) return;
      if (rw > 0 && rw < 160) return;          // 渲染过小 → 装饰图（隐藏元素 rw=0 不判）
      out.push({ src, w, h, alt: (alt || '').slice(0, 60), rw });
    };
    document.querySelectorAll('img').forEach(img => {
      let src = img.currentSrc || img.src || img.dataset.src || img.dataset.original || img.dataset.lazy || '';
      if (!src && img.srcset) src = img.srcset.split(',')[0].trim().split(' ')[0];
      push(src, img.naturalWidth || img.width, img.naturalHeight || img.height,
           img.alt, Math.round(img.getBoundingClientRect().width));
    });
    // 兜底：CSS 背景图（营销页常见）
    if (out.length < 4) {
      document.querySelectorAll('*').forEach(n => {
        const bg = getComputedStyle(n).backgroundImage;
        if (!bg || bg === 'none' || bg.includes('gradient')) return;
        const m = bg.match(/url\(["']?([^"')]+)["']?\)/);
        if (!m) return;
        const r = n.getBoundingClientRect();
        if (r.width >= minW) push(m[1], r.width * 2, r.height * 2, (n.className || '').toString().slice(0, 40), r.width);
      });
    }
    return out;
  }, { minW, minH });

  // 按文档顺序去重，过滤装饰图
  const seen = new Set();
  const picked = [];
  cands.forEach(c => {
    if (picked.length >= max) return;
    if (seen.has(c.src)) return;
    if (BAD_SRC.test(c.src)) return;
    seen.add(c.src);
    picked.push(c);
  });

  const files = [];
  for (let i = 0; i < picked.length; i++) {
    const c = picked[i];
    try {
      const resp = await ctx.request.get(c.src, { timeout: 45000 });
      if (!resp.ok()) throw new Error('HTTP ' + resp.status());
      const buf = await resp.body();
      if (buf.length < 12000) throw new Error('文件过小 ' + buf.length + 'B');
      let ext = '.png';
      const url = c.src.split('?')[0].toLowerCase();
      if (/\.(jpe?g)$/.test(url)) ext = '.jpg';
      else if (/\.webp$/.test(url)) ext = '.webp';
      const file = path.join(OUT, `${t.name}_${String(i + 1).padStart(2, '0')}${ext}`);
      fs.writeFileSync(file, buf);
      files.push({ file, w: c.w, h: c.h, alt: c.alt, from: c.src });
    } catch (e) {
      console.log('  跳过图片', c.src.slice(-60), '→', e.message.slice(0, 50));
    }
  }
  await page.close();
  return files;
}

(async () => {
  const launchOpts = {
    headless: true,
    args: ['--no-sandbox', '--disable-blink-features=AutomationControlled', '--lang=zh-CN']
  };
  if (EXE) launchOpts.executablePath = EXE;
  console.log('[browser]', EXE || '(playwright 默认)');
  const browser = await chromium.launch(launchOpts);
  const ctx = await browser.newContext({
    userAgent: UA, locale: 'zh-CN', deviceScaleFactor: 2,
    viewport: { width: 1440, height: 900 }
  });
  await ctx.addInitScript(() => { Object.defineProperty(navigator, 'webdriver', { get: () => undefined }); });

  const manifest = [];
  for (const t of CFG.targets || []) {
    console.log(`▶ [${t.mode || 'page'}] ${t.name}  ${t.url}`);
    try {
      if ((t.mode || 'page') === 'imgs') {
        const files = await shootImgs(ctx, t);
        files.forEach(f => {
          const kb = Math.round(fs.statSync(f.file).size / 1024);
          console.log(`  ✓ ${path.basename(f.file)}  ${f.w}x${f.h}  ${kb}KB`);
          manifest.push({ name: t.name, file: path.basename(f.file), w: f.w, h: f.h, alt: f.alt, url: t.url, kb });
        });
        if (!files.length) console.log('  ✗ 未找到合格的产品界面图；换官方帮助文档/产品页 URL');
      } else {
        const file = await shootPage(ctx, t);
        const kb = Math.round(fs.statSync(file).size / 1024);
        console.log(`  ✓ ${path.basename(file)}  ${kb}KB`);
        manifest.push({ name: t.name, file: path.basename(file), url: t.url, kb, mode: 'page' });
      }
    } catch (e) {
      console.log('  ✗ 失败：' + e.message.slice(0, 100));
    }
  }
  fs.writeFileSync(path.join(OUT, '_manifest.json'), JSON.stringify(manifest, null, 2));
  await browser.close();
  console.log(`\n共 ${manifest.length} 张 → ${OUT}`);
})();
