// Run against disposable study data. This test deletes a fixture course.
async (page) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.reload();

  const sidebar = page.getByRole('complementary');
  const course = sidebar.getByRole('combobox', { name: 'Học phần đang chọn' });
  const action = (name) => sidebar.getByRole('button', { name, exact: true });
  const heading = (name) => page.getByRole('heading', { name, exact: true, level: 1 });
  const edit = action('Đổi tên học phần');
  const remove = action('Xóa học phần');
  const cancel = action('Hủy');
  const originalName = 'Toán rời rạc';
  const updatedName = 'Toán rời rạc – Ôn tập';
  const requirementsName = 'Thu thập và phân tích yêu cầu';
  const mathId = 'toan_roi_rac';
  const mathOption = page.locator(`#course-select option[value="${mathId}"]`);

  await course.selectOption(mathId);
  await edit.click({ timeout: 3000 });
  const name = sidebar.getByRole('textbox', { name: 'Tên mới của học phần' });
  if (await name.inputValue() !== originalName) throw new Error('Original course name was not prefilled');
  await name.fill('   ');
  if (await action('Lưu tên').isEnabled()) throw new Error('An empty course name can be submitted');
  await name.fill(requirementsName);
  await action('Lưu tên').click();
  await sidebar.getByRole('alert').filter({ hasText: 'Tên học phần này đã có.' }).waitFor({ state: 'visible' });
  await heading(originalName).waitFor({ state: 'visible' });
  if (await name.inputValue() !== requirementsName) throw new Error('The rejected draft was lost');
  console.log('HP-01 · Từ chối tên rỗng và tên trùng, giữ nội dung để sửa lại.');

  await name.fill(updatedName);
  await name.press('Enter');
  await heading(updatedName).waitFor({ state: 'visible' });
  await sidebar.getByText('discrete_math_study.pdf', { exact: true }).waitFor({ state: 'visible' });
  await page.reload();
  await heading(updatedName).waitFor({ state: 'visible' });
  if (await course.inputValue() !== mathId) throw new Error('Rename changed course identity');
  console.log('HP-02 · Đổi tên, giữ PDF và giữ tên mới sau khi tải lại.');

  await remove.click();
  const confirmation = sidebar.getByRole('group', { name: 'Xác nhận xóa học phần' });
  await confirmation.getByText(updatedName, { exact: true }).waitFor({ state: 'visible' });
  await cancel.click();
  await confirmation.waitFor({ state: 'hidden' });
  await heading(updatedName).waitFor({ state: 'visible' });
  if (!await mathOption.count()) throw new Error('Cancel removed the course');
  console.log('HP-03 · Hủy xác nhận xóa và giữ học phần.');

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: 'Mở menu điều hướng' }).click();
  await remove.click();
  await confirmation.waitFor({ state: 'visible' });
  const overflows = await sidebar.evaluate((element) => element.scrollWidth > element.clientWidth);
  if (overflows) throw new Error('Course management overflows the mobile sidebar');
  await action('Xác nhận xóa').click();
  await heading(requirementsName).waitFor({ state: 'visible' });
  if (await mathOption.count()) throw new Error('Deleted course is still listed');
  await page.reload();
  await heading(requirementsName).waitFor({ state: 'visible' });
  if (await mathOption.count()) throw new Error('Deleted course reappeared after reload');
  if (errors.length) throw new Error(errors.join('\n'));
  console.log('HP-04 · Xóa trên màn hình 390 px, chuyển học phần và giữ kết quả sau tải lại.');
}
