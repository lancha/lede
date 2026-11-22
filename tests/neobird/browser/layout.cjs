// Synthetic rendering checks run on an isolated GitHub runner, never on the router.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');
const output = process.env.NEOBIRD_TEST_OUTPUT || 'neobird-layout-results';
const base = 'http://127.0.0.1:8876/tests/neobird/preview.html';

(async () => {
  await fs.mkdir(output, { recursive: true });
  const browser = await chromium.launch();
  let failures = 0;
  const results = [];
  try {
    for (const width of [1440, 1024, 390, 320]) {
      for (const scheme of ['light', 'dark']) {
        const name = `${width}-${scheme}`;
        const page = await browser.newPage({viewport: {width, height: 900}, colorScheme: scheme});
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        try {
          await page.goto(`${base}?scheme=${scheme}`);
          await page.waitForFunction(() => document.querySelector('#checks').textContent.includes('PASS'));
          const checks = await page.locator('#checks').textContent();
          assert.ok(!checks.includes('FAIL'), checks);
          const cardColor = await page.locator('#system-card').evaluate(el => getComputedStyle(el).backgroundColor);
          assert.equal(cardColor, scheme === 'dark' ? 'rgb(28, 28, 30)' : 'rgb(255, 255, 255)');
          const progress = await page.locator('.cbi-progressbar').boundingBox();
          const progressFill = await page.locator('.cbi-progressbar > div').boundingBox();
          assert.equal(progress.height, 20, 'native progress bar must be visible');
          assert.ok(progressFill.width > 0 && progressFill.width < progress.width, 'progress fill must be proportional');
          if (width <= 992) {
            await page.getByRole('button', {name:'Menu', exact:true}).click();
            assert.equal(await page.locator('.showSide').getAttribute('aria-expanded'), 'true');
            await page.locator('.darkMask').click({position: {x:width - 10, y:100}});
            assert.equal(await page.locator('.showSide').getAttribute('aria-expanded'), 'false');
          }
          await page.locator('#protocol').click();
          const dropdown = page.locator('#protocol > ul.dropdown');
          assert.equal(await page.locator('#protocol').getAttribute('open'), '');
          await dropdown.getByText('静态地址', {exact:true}).click();
          await page.getByRole('button', {name:'测试弹窗'}).click();
          await page.getByRole('dialog').waitFor({state:'visible'});
          const modalBox = await page.getByRole('dialog').boundingBox();
          assert.ok(modalBox.x >= 0 && modalBox.x + modalBox.width <= width + 1, 'modal overflows');
          await page.getByRole('button', {name:'关闭', exact:true}).last().click();
          await page.locator('#modal_overlay').waitFor({state:'hidden'});
          await page.locator('.cbi-page-actions').scrollIntoViewIfNeeded();
          const actions = await page.locator('.cbi-page-actions').boundingBox();
          const nav = await page.locator('#neobird-quicklinks').boundingBox();
          assert.ok(actions.y + actions.height <= nav.y + 1, 'bottom bar covers actions');
          await page.screenshot({path:path.join(output, `${name}-actions.png`)});
          await page.evaluate(() => scrollTo(0, 0));
          await page.screenshot({path:path.join(output, `${name}.png`)});
          await page.goto(`${base}?scheme=${scheme}&login=1`);
          await page.getByRole('button', {name:'登录', exact:true}).waitFor();
          assert.equal(await page.locator('#mainmenu').isVisible(), false);
          assert.equal(await page.locator('#neobird-quicklinks').isVisible(), false);
          const login = await page.locator('#maincontent > .container').boundingBox();
          assert.ok(login.x >= 0 && login.x + login.width <= width + 1, 'login overflows');
          await page.screenshot({path:path.join(output, `${name}-login.png`)});
          assert.deepEqual(errors, []);
          results.push({name, status:'passed', checks});
          console.log(`PASS ${name}: cards, progress, navigation, popup, actions, login`);
        } catch (error) {
          failures++;
          results.push({name, status:'failed', error:String(error), errors});
          console.error(`FAIL ${name}: ${error.stack}`);
          await page.screenshot({path:path.join(output, `${name}-failure.png`)}).catch(() => {});
        } finally {
          await page.close();
        }
      }
    }
  } finally {
    await browser.close();
    await fs.writeFile(path.join(output, 'results.json'), JSON.stringify(results, null, 2) + '\n');
  }
  process.exitCode = failures ? 1 : 0;
})().catch(error => { console.error(error); process.exitCode = 1; });
