// End-to-end test of the no-login homework page: node virtual-lab/homework.test.cjs
// Needs LAB_URL (site root ending with /) and CHROME_PATH. No accounts are used; everything stays in the test browser.
const {chromium} = require('playwright-core');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');

const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAIAAAACUFjqAAAAFElEQVR42mP8z8Dwn4EIwMiAEgEAU2oC/cJ5Qx8AAAAASUVORK5CYII=', 'base64');
const SID = 'B2405.010133', CASE = 3;

(async () => {
  const {workload, scheduling, replacement, allocation, synchronization} = await import(path.join(__dirname, 'engine.mjs').replace(/\\/g, '/').replace(/^([A-Za-z]):/, 'file:///$1:'));
  const w = workload(SID, CASE);
  const answers = {cpu: scheduling(w.processes, 'RR', w.quantum).averageWaiting, sync: synchronization(w.sync, false).counter, vm: replacement(w.pages, w.frames, 'LRU').faults, fs: allocation(w.fileKiB, w.blockKiB, w.freeBlocks).blocks};
  const url = process.env.LAB_URL + 'homework';
  const browser = await chromium.launch({executablePath: process.env.CHROME_PATH, headless: true});
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'oslab-hw-'));
  try {
    const ctx = await browser.newContext({acceptDownloads: true});
    const page = await ctx.newPage();
    page.on('dialog', d => d.accept());
    await page.goto(url);

    // invalid student number is refused
    await page.getByLabel('Student number').fill('12345');
    await page.getByRole('button', {name: 'Start / continue'}).click();
    assert.match(await page.locator('#startMsg').textContent(), /student number exactly/);

    // start
    await page.getByLabel('Student number').fill(' b2405.010133 ');
    await page.getByLabel('Name and surname (printed on your report)').first().fill('Synthetic Student');
    await page.getByLabel('Choose one system').selectOption(String(CASE));
    await page.getByRole('button', {name: 'Start / continue'}).click();
    await page.getByRole('heading', {name: 'Hospital Patient Monitoring System'}).waitFor();
    assert.ok((await page.locator('#sec-cpu').textContent()).includes('Quantum: ' + w.quantum + ' ms'), 'workload comes from the student number');

    // written parts and images
    const fill = (label, text) => page.getByLabel(label, {exact: false}).first().fill(text);
    await fill('Describe your components', 'Sensors -> monitor service -> alarm service');
    await fill('Processes, threads and shared resources', 'Monitor process with reader and alarm threads');
    await fill('Deadlock: P1 holds lock A', 'Circular wait; acquire A before B');
    await fill('File locking: what can a reader see', 'Mixed versions; shared lock for readers, exclusive for writer');
    await fill('Record CPU, memory, disk and thread measurements', 'CPU 12% -> 64% for 2 minutes');
    for (const [i, name] of ['diagram', 'baseline', 'load'].entries())
      await page.locator('input[type=file]').nth(i + 1).setInputFiles({name: name + '.png', mimeType: 'image/png', buffer: PNG});
    await page.waitForFunction(() => document.querySelectorAll('img.evidence:not([hidden])').length === 3);

    // locking needs both a number and the working
    await page.locator('#pred-cpu').fill(String(answers.cpu));
    await page.locator('#sec-cpu').getByRole('button', {name: /Lock my prediction/}).click();
    assert.equal(await page.locator('#pred-cpu').count(), 1, 'prediction must not lock without working');
    const predictions = {cpu: answers.cpu, sync: answers.sync, vm: answers.vm + 1, fs: answers.fs};
    for (const k of ['cpu', 'sync', 'vm', 'fs']) {
      await page.locator('#pred-' + k).fill(String(predictions[k]));
      await page.locator('#work-' + k).fill('Working for ' + k);
      await page.locator('#sec-' + k).getByRole('button', {name: /Lock my prediction/}).click();
      await page.locator('#sec-' + k + ' .locked').waitFor();
      assert.ok((await page.locator('#sec-' + k + ' .locked').textContent()).includes('Simulation result: ' + Number(answers[k].toFixed(2))), k + ' simulation result');
      await page.locator('#f-' + k + 'Correction').fill('Comparison for ' + k);
    }
    assert.ok((await page.locator('#sec-cpu .sim').textContent()).includes('Gantt:'), 'step-by-step simulation is shown');
    await page.getByRole('button', {name: 'Download progress file'}).waitFor();
    assert.match(await page.locator('#checklist').textContent(), /Everything is complete/);

    // continue where you left off after closing the page
    await page.reload();
    assert.ok(await page.getByRole('button', {name: 'Continue Hospital Patient Monitoring System'}).isVisible(), 'saved case is listed');
    await page.getByRole('button', {name: 'Continue Hospital Patient Monitoring System'}).click();
    assert.equal(await page.locator('#f-evaluation').inputValue(), 'CPU 12% -> 64% for 2 minutes');
    assert.equal(await page.locator('#pred-vm').count(), 0, 'locked predictions stay locked');
    assert.ok((await page.locator('#sec-vm .locked').textContent()).includes('Initial prediction: ' + predictions.vm));

    // a second system keeps its own work
    await page.getByRole('button', {name: 'Change student number or system'}).click();
    await page.getByLabel('Choose one system').selectOption('1');
    await page.getByRole('button', {name: 'Start / continue'}).click();
    await fill('Describe your components', 'Gaming draft');
    await page.getByRole('button', {name: 'Change student number or system'}).click();
    assert.equal(await page.locator('#saved button').count(), 2, 'both systems are listed');

    // progress file moves the work to another computer
    await page.getByRole('button', {name: 'Continue Hospital Patient Monitoring System'}).click();
    const [download] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', {name: 'Download progress file'}).click()]);
    const file = path.join(tmp, download.suggestedFilename()); await download.saveAs(file);
    const other = await (await browser.newContext()).newPage();
    other.on('dialog', d => d.accept());
    await other.goto(url);
    await other.locator('#importFile').setInputFiles(file);
    await other.getByRole('heading', {name: 'Hospital Patient Monitoring System'}).waitFor();
    assert.equal(await other.locator('#f-architecture').inputValue(), 'Sensors -> monitor service -> alarm service');
    assert.equal(await other.locator('img.evidence:not([hidden])').count(), 3, 'images travel with the progress file');
    await other.locator('#importFile').setInputFiles({name: 'bad.json', mimeType: 'application/json', buffer: Buffer.from('{"x":1}')}).catch(() => {});

    // a different student gets different numbers
    const third = await (await browser.newContext()).newPage();
    await third.goto(url);
    await third.getByLabel('Student number').fill('B2405.010134');
    await third.getByLabel('Choose one system').selectOption(String(CASE));
    await third.getByRole('button', {name: 'Start / continue'}).click();
    await third.locator('#sec-cpu').waitFor();
    const mine = workload(SID, CASE), theirs = workload('B2405.010134', CASE);
    assert.notDeepEqual(theirs.pages, mine.pages);
    assert.ok((await third.locator('#sec-vm').textContent()).includes(theirs.pages.join(', ')));

    // PDF report
    await page.emulateMedia({media: 'print'});
    assert.ok(await page.locator('#reportHead').isVisible(), 'report header is printed');
    assert.ok((await page.locator('#reportHead').textContent()).includes(SID));
    assert.ok(!(await page.locator('#startSec').isVisible()), 'start form is not printed');
    const pdf = await page.pdf();
    assert.equal(pdf.subarray(0, 4).toString(), '%PDF');
    console.log('PASS homework: student number, case choice, autosave and resume, locked predictions, separate systems, progress file transfer, different numbers per student, checklist, PDF ' + pdf.length + ' bytes');
  } finally { await browser.close(); fs.rmSync(tmp, {recursive: true, force: true}); }
})().catch(e => { console.error(e.message); process.exitCode = 1; });
