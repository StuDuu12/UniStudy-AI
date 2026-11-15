// Run with playwright-cli run-code against a fresh browser profile and disposable study data.
async (page) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.reload();

  const button = (name) => page.getByRole('button', { name, exact: true });
  const tab = () => button('Học cùng AI').click();
  const studyRegion = page.getByRole('region', { name: 'Học cùng AI' });
  const topic = (name) => studyRegion.getByRole('button', { name: new RegExp('^' + name) }).click();
  const text = (value) => page.getByText(value).first().waitFor({ state: 'visible' });
  const answer = page.getByRole('textbox', { name: 'Câu trả lời của bạn' });
  const course = page.locator('aside').getByRole('combobox');
  const chooseTesting = () => course.selectOption('software_testing');

  async function submit(values) {
    await answer.fill(values);
    await button('Kiểm tra câu trả lời').click();
  }

  await chooseTesting();
  const draft = page.getByRole('textbox', { name: 'Câu hỏi', exact: true });
  await draft.fill('Bản nháp thử chế độ học');
  await tab();
  await button('Hỏi đáp').click();
  if (await draft.inputValue() !== 'Bản nháp thử chế độ học') throw new Error('Q&A draft was lost');
  const question = 'Phân vùng tương đương là gì?';
  await draft.fill(question);
  await button('Gửi câu hỏi').click();
  const savedChat = page.locator('aside').getByText(question, { exact: true }).first();
  await savedChat.waitFor({ state: 'visible' });
  await tab();
  await savedChat.click();
  if (await button('Hỏi đáp').getAttribute('aria-pressed') !== 'true') {
    throw new Error('Selecting a chat did not open the Q&A view');
  }
  console.log('UI-01 · Giữ bản nháp khi đổi chế độ và mở lại Hỏi đáp từ lịch sử.');

  await tab();
  await topic('Phân vùng tương đương');
  const firstResponsePattern = '**/api/study/software_testing/equivalence';
  await page.route(firstResponsePattern, async (route) => {
    if (route.request().postDataJSON()?.action === 'submit') {
      const serverReply = await route.fetch();
      if (!serverReply.ok()) throw new Error('First study attempt was not committed');
      await route.abort();
    } else {
      await route.continue();
    }
  });
  await submit('21, 24, 28');
  await page.getByRole('alert').getByText(/Mất kết nối/).waitFor({ state: 'visible' });
  await page.unroute(firstResponsePattern);
  await page.reload();
  await chooseTesting();
  await tab();
  await topic('Phân vùng tương đương');
  await text(/cùng một lớp/);
  console.log('UI-08 · Khôi phục bước giải thích khi mất phản hồi của lần nộp đầu.');

  await button('Phân vùng tương đương · Trang PDF 2').click();
  await page.getByRole('img', { name: 'Tài liệu software_testing.pdf - Trang 2' }).waitFor({ state: 'visible' });
  await page.waitForFunction(() => {
    const image = document.querySelector('img[alt="Tài liệu software_testing.pdf - Trang 2"]');
    return image && image.complete && image.naturalWidth > 0;
  });
  const pdfLink = await page.getByRole('link', { name: 'Mở tab mới' }).getAttribute('href');
  if (!pdfLink?.endsWith('/testing_basics#page=2')) throw new Error('PDF did not open on page 2');
  await button('Đóng').click();
  console.log('UI-02 · Mở trình xem PDF từ trang nguồn của lời giải thích.');

  const ai = button('Giải thích thêm với AI');
  const canTestAI = await ai.isVisible();
  if (canTestAI) {
    await ai.click();
    await page.getByRole('heading', { name: 'Giải thích thêm của AI' }).waitFor({ state: 'visible', timeout: 120000 });
    await button('[1] Trang PDF 2').waitFor({ state: 'visible' });
    console.log('UI-03 · Hiển thị lời giải thích AI có nút mở trang nguồn.');

    const routePattern = '**/api/study/software_testing/equivalence';
    let finishDelay;
    const delay = new Promise((resolve) => { finishDelay = resolve; });
    await page.route(routePattern, async (route) => {
      if (route.request().postDataJSON()?.action === 'ai') {
        await delay;
        await route.abort().catch(() => {});
      } else {
        await route.continue();
      }
    });
    try {
      await ai.click();
      await text(/Đang tạo giải thích/);
      await button('Tự làm bài mới').click({ timeout: 3000 });
      await text(/5 đến 12/);
      console.log('UI-04 · Chuyển sang tự làm khi AI đang chờ phản hồi.');
    } finally {
      finishDelay();
      await page.unroute(routePattern);
    }
  } else {
    await button('Tự làm bài mới').click();
    console.log('UI-03 và UI-04 · Bỏ qua vì máy chủ chưa cấu hình AI.');
  }

  await submit('4.5 7 13');
  await page.getByRole('alert').getByText(/Nhập các số nguyên/).waitFor({ state: 'visible' });

  await page.route('**/api/study/software_testing/equivalence', (route) => route.abort());
  await submit('4 7 13');
  await page.getByRole('alert').getByText(/Mất kết nối/).waitFor({ state: 'visible' });
  if (await answer.inputValue() !== '4 7 13') throw new Error('Study response was lost on network failure');
  await page.unroute('**/api/study/software_testing/equivalence');
  await button('Kiểm tra câu trả lời').click();
  await page.getByRole('heading', { name: 'Đã tự làm đúng' }).waitFor({ state: 'visible' });
  console.log('UI-05 · Từ chối số thập phân, giữ câu trả lời qua mất mạng, gửi lại thành công.');

  await page.reload();
  await chooseTesting();
  await tab();
  await page.getByRole('button', { name: /^Phân vùng tương đương.*Đã tự làm đúng/ }).waitFor({ state: 'visible' });
  await topic('Phân vùng tương đương');
  await page.getByRole('heading', { name: 'Đã tự làm đúng' }).waitFor({ state: 'visible' });
  await button('Ôn với dữ kiện khác').click();
  await text(/3 đến 9/);
  await button('Các bài học').click();
  await course.selectOption('algorithm_analysis');
  await text(/Chọn học phần Kiểm thử phần mềm/);
  await chooseTesting();
  await page.getByRole('button', { name: /^Phân vùng tương đương.*Đã tự làm đúng/ }).waitFor({ state: 'visible' });
  console.log('UI-06 · Khôi phục và tách tiến độ theo học phần, ôn lại với dữ kiện khác.');

  await page.setViewportSize({ width: 390, height: 844 });
  await topic('Phân tích giá trị biên');
  await button('Xem giải thích trước').click();
  await button('Tự làm bài mới').click();
  await button('Xem gợi ý').click();
  await button('Gợi ý tiếp theo').click();
  await text(/cộng và trừ 1/);
  await submit('0 1 2 9 10 11');
  await page.getByRole('heading', { name: 'Cần luyện thêm' }).waitFor({ state: 'visible' });
  const hasOverflow = await page.getByRole('region', { name: 'Học cùng AI' }).evaluate((region) =>
    region.scrollWidth > region.clientWidth || document.documentElement.scrollWidth > innerWidth);
  if (hasOverflow) throw new Error('Mobile page overflows horizontally');
  await button('Mở menu điều hướng').click();
  await page.locator('aside').getByRole('button', { name: 'Hội thoại mới' }).click();
  if (await button('Hỏi đáp').getAttribute('aria-pressed') !== 'true') {
    throw new Error('Creating a chat did not open the Q&A view');
  }
  if (errors.length) throw new Error(errors.join('\n'));
  console.log('UI-07 · Luồng 390 px, làm bài có gợi ý và quay về hỏi đáp.');
}
