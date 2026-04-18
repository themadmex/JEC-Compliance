async (page) => {
  await page.context().unroute("**/auth/me").catch(() => {});
  await page.context().route("**/auth/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 1,
        email: "designer@jec.local",
        name: "Nnaemeka Ugwokegbe",
        role: "compliance_manager",
      }),
    }),
  );
}
