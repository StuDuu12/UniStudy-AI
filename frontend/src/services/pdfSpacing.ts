// Older PDF excerpts were stored with these Vietnamese words joined together.
const knownPhrases = [
  'thể là', 'hệ thống', 'đặc tính', 'sử dụng',
  'sở để', 'sở để thương', 'sở để xác', 'kỹ thuật',
  'kỹ nghệ', 'kỹ nghệ yêu', 'tả sản', 'sở cho',
  'thể xung', 'bổ sung', 'ngữ tự nhiên', 'về các',
  'vụ tài', 'đồ lớp', 'đồ đối', 'thẻ CRC',
  'đồ tuần', 'đồ cộng', 'đồ tương', 'đồ trạng', 'đồ giao',
  // Glued words from slide decks and textbooks
  'thể vừa', 'đồ thị', 'cả m cạnh', 'độ tin',
  'từ góc độ người', 'từ góc', 'độ người',
  'quan hệ giữa', 'hệ giữa',
  'được kết', 'nghiệp vụ',
];

const phraseReplacements: [RegExp, string][] = [
  [/cảm cạnh/gi, 'cả m cạnh'],
  [/từgóc độngười/gi, 'từ góc độ người'],
  [/từgócđộngười/gi, 'từ góc độ người'],
  [/quan hệgiữa/gi, 'quan hệ giữa'],
  [/thểvừa/gi, 'thể vừa'],
  [/đồthị/gi, 'đồ thị'],
  [/độtin/gi, 'độ tin'],
  [/đượckết/gi, 'được kết'],
  [/nghiệpvụ/gi, 'nghiệp vụ'],
];

// Strip email footprints like longth@hnue.edu.vn and associated trailing page numbers
const EMAIL_FOOTPRINT_REGEX = /(?:email:\s*)?[\w.-]+@[\w.-]+\.[a-zA-Z]{2,}(?:\s*\d+)?/gi;

// Strip standalone stray page numbers (lines consisting solely of digits 1-3)
const STRAY_PAGE_NUMBER_REGEX = /(?:^|[\r\n])[ \t]*\d{1,3}[ \t]*(?=[\r\n]|$)/gu;

// Convert slide bullet artifacts (❑, , Ø, , \uf071, etc.) into clean bullets "• "
// eslint-disable-next-line no-control-regex
const BULLET_ARTIFACTS_REGEX = /[❑\uf071\uf076\x11■□▪▫►▸◆][ \t]*/gu;
const LEADING_OE_BULLET_REGEX = /(?:^|[\r\n])[ \t]*Ø[ \t]*/gu;
const INLINE_OE_BULLET_REGEX = /(?<=[ \t])Ø[ \t]+(?=[\p{L}\p{M}])/gu;

const segmentsByWord = new Map(knownPhrases.map((phrase) => {
  const segments = phrase.split(' ');
  return [segments.join('').toLowerCase(), segments];
}));

export function restorePdfWordSpacing(text: string): string {
  if (!text) return '';

  // 1. Strip email footprints
  let result = text.replace(EMAIL_FOOTPRINT_REGEX, '');

  // 2. Strip standalone stray page numbers
  result = result.replace(STRAY_PAGE_NUMBER_REGEX, '');

  // 3. Clean slide bullet artifacts into clean bullets "• "
  result = result.replace(BULLET_ARTIFACTS_REGEX, '• ');
  result = result.replace(LEADING_OE_BULLET_REGEX, (m) => (m.startsWith('\n') ? '\n• ' : m.startsWith('\r') ? '\r• ' : '• '));
  result = result.replace(INLINE_OE_BULLET_REGEX, '• ');

  // 4. Apply multi-word phrase replacements
  for (const [pattern, replacement] of phraseReplacements) {
    result = result.replace(pattern, replacement);
  }

  // 5. Restore glued words matching known segments
  result = result.replace(/[\p{L}\p{M}\p{N}_]+/gu, (word) => {
    const normalized = word.normalize('NFC');
    const segments = segmentsByWord.get(normalized.toLowerCase());
    if (!segments) return word;

    // Keep the capitalization of the original excerpt.
    let offset = 0;
    return segments.map((segment) => {
      const start = offset;
      offset += segment.length;
      return normalized.slice(start, offset);
    }).join(' ');
  });

  // 6. Clean up excessive consecutive blank lines
  result = result.replace(/\n\s*\n\s*\n+/g, '\n\n');

  return result;
}

export function formatSourceExcerpt(rawExcerpt: string): string {
  const cleaned = restorePdfWordSpacing(rawExcerpt);
  return cleaned
    .replace(/(?<=\S)[ \t]+•[ \t]*/g, '\n• ')
    .replace(/(?:^|\n)[ \t]*•[ \t]*/g, '\n• ')
    .replace(/(?<=\S)[ \t]+(?=(?:\d{1,2}[.)]|[a-zA-Z][.)])[ \t]+[\p{L}\p{M}])/gu, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

