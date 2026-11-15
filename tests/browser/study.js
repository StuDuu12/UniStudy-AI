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
  const prompt = studyRegion.locator('#study-prompt');
  const course = page.locator('aside').getByRole('combobox');
  const chooseMath = () => course.selectOption('toan_roi_rac');
  const chooseRequirements = () => course.selectOption('thu_thap_phan_tich_yeu_cau');
  const mathLesson = 'Phép hợp và phép giao';
  const requirementsLesson = 'Yêu cầu chức năng và phi chức năng';
  const mathTurn = '**/api/study/toan_roi_rac/union';
  const completedMathLesson = studyRegion.getByRole('button', { name: /^Phép hợp và phép giao.*Đã tự làm đúng/ });

  async function submit(values) {
    await answer.fill(values);
    await button('Kiểm tra câu trả lời').click();
  }

  await chooseMath();
  const draft = page.getByRole('textbox', { name: 'Câu hỏi', exact: true });
  await draft.fill('Bản nháp thử chế độ học');
  await tab();
  await button('Hỏi đáp').click();
  if (await draft.inputValue() !== 'Bản nháp thử chế độ học') throw new Error('Q&A draft was lost');
  const question = 'Phép hợp và phép giao khác nhau thế nào?';
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
  await topic(mathLesson);
  await page.route(mathTurn, async (route) => {
    if (route.request().postDataJSON()?.action === 'submit') {
      const serverReply = await route.fetch();
      if (!serverReply.ok()) throw new Error('First study attempt was not committed');
      await route.abort();
    } else {
      await route.continue();
    }
  });
  await submit('4');
  await page.getByRole('alert').getByText(/Mất kết nối/).waitFor({ state: 'visible' });
  await page.unroute(mathTurn);
  await page.reload();
  await chooseMath();
  await tab();
  await topic(mathLesson);
  await studyRegion.getByRole('status').filter({ hasText: 'phần giao' }).waitFor({ state: 'visible' });
  console.log('UI-08 · Khôi phục bước giải thích khi mất phản hồi của lần nộp đầu.');

  await button(mathLesson + ' · Trang PDF 1').click();
  await page.getByRole('img', { name: 'Tài liệu discrete_math_study.pdf - Trang 1' }).waitFor({ state: 'visible' });
  await page.waitForFunction(() => {
    const image = document.querySelector('img[alt="Tài liệu discrete_math_study.pdf - Trang 1"]');
    return image && image.complete && image.naturalWidth > 0;
  });
  const pdfLink = await page.getByRole('link', { name: 'Mở tab mới' }).getAttribute('href');
  if (!pdfLink?.endsWith('/discrete_math_study#page=1')) throw new Error('PDF did not open on page 1');
  await button('Đóng').click();
  console.log('UI-02 · Mở trình xem PDF từ trang nguồn của lời giải thích.');

  const ai = button('Giải thích thêm với AI');
  await ai.click();
  await page.getByRole('heading', { name: 'Giải thích thêm của AI' }).waitFor({ state: 'visible', timeout: 120000 });
  await text(/vì sao số 0 thuộc phép hợp/);
  await button('[1] Trang PDF 1').waitFor({ state: 'visible' });
  console.log('UI-03 · Hiển thị lời giải thích AI có nút mở trang nguồn.');

  let finishDelay;
  const delay = new Promise((resolve) => { finishDelay = resolve; });
  await page.route(mathTurn, async (route) => {
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
    await prompt.filter({ hasText: 'A = {-3, 2, 5} và B = {2, 6}' }).waitFor({ state: 'visible' });
    console.log('UI-04 · Chuyển sang tự làm khi AI đang chờ phản hồi.');
  } finally {
    finishDelay();
    await page.unroute(mathTurn);
  }

  await submit('-3.5 2 5 6');
  await page.getByRole('alert').getByText(/Nhập các số nguyên/).waitFor({ state: 'visible' });

  await page.route(mathTurn, (route) => route.abort());
  await submit('-3 2 5 6');
  await page.getByRole('alert').getByText(/Mất kết nối/).waitFor({ state: 'visible' });
  if (await answer.inputValue() !== '-3 2 5 6') throw new Error('Study response was lost on network failure');
  await page.unroute(mathTurn);
  await button('Kiểm tra câu trả lời').click();
  await page.getByRole('heading', { name: 'Đã tự làm đúng' }).waitFor({ state: 'visible' });
  console.log('UI-05 · Từ chối số thập phân, giữ câu trả lời qua mất mạng, gửi lại thành công.');

  await page.reload();
  await chooseMath();
  await tab();
  await completedMathLesson.waitFor({ state: 'visible' });
  await topic(mathLesson);
  await page.getByRole('heading', { name: 'Đã tự làm đúng' }).waitFor({ state: 'visible' });
  await button('Ôn với dữ kiện khác').click();
  await prompt.filter({ hasText: 'A = {2, 9} và B = {-2, 9, 11}' }).waitFor({ state: 'visible' });
  await button('Các bài học').click();
  await chooseRequirements();
  await studyRegion.getByRole('button', { name: /^Yêu cầu chức năng và phi chức năng.*Chưa bắt đầu/ }).waitFor({ state: 'visible' });
  await completedMathLesson.waitFor({ state: 'hidden' });
  await chooseMath();
  await completedMathLesson.waitFor({ state: 'visible' });
  console.log('UI-06 · Khôi phục và tách tiến độ theo học phần, ôn lại với dữ kiện khác.');

  await chooseRequirements();
  await page.setViewportSize({ width: 390, height: 844 });
  await topic(requirementsLesson);
  await button('Xem giải thích trước').click();
  await button(requirementsLesson + ' · Trang PDF 1').waitFor({ state: 'visible' });
  await button('Tự làm bài mới').click();
  await prompt.filter({ hasText: 'Một ứng dụng quản lý phòng học' }).waitFor({ state: 'visible' });
  await button('Xem gợi ý').click();
  await button('Gợi ý tiếp theo').click();
  await studyRegion.getByRole('status').filter({ hasText: 'hành động' }).waitFor({ state: 'visible' });
  await submit('2 4');
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
