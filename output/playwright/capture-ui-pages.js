async (page) => {
  const pages = [
    ["home", "http://127.0.0.1:8000/#home"],
    ["controls", "http://127.0.0.1:8000/#compliance-controls"],
    ["control-detail", "http://127.0.0.1:8000/?control=AST-1#compliance-controls"],
    ["evidence-detail", "http://127.0.0.1:8000/?evidence=1#evidence"],
    ["tests", "http://127.0.0.1:8000/#tests"],
    ["test-detail", "http://127.0.0.1:8000/?test=TST-1#tests"],
    ["audits", "http://127.0.0.1:8000/#compliance-audits"],
    ["audit-detail", "http://127.0.0.1:8000/?audit=1#compliance-audits"],
    ["auditor-portal", "http://127.0.0.1:8000/?audit=1#auditor-portal"],
  ];
  const report = [];
  for (const [name, url] of pages) {
    await page.goto(url, { waitUntil: "networkidle" });
    await page.waitForTimeout(500);
    const path = `output/playwright/${name}.png`;
    await page.screenshot({ path, fullPage: true });
    const metrics = await page.evaluate(() => {
      const main = document.querySelector("main");
      const body = document.body;
      return {
        title: document.querySelector("main h1, main h2")?.textContent?.trim() || "",
        screenError: document.body.innerText.includes("Screen Error"),
        horizontalOverflow: body.scrollWidth > window.innerWidth + 2,
        bodyWidth: body.scrollWidth,
        viewportWidth: window.innerWidth,
        mainHeight: main?.scrollHeight || 0,
      };
    });
    report.push({ name, path, url: page.url(), ...metrics });
  }
  return report;
}
