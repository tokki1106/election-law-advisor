import { marked } from 'marked';

marked.setOptions({
  breaks: true,
  gfm: true,
});

/**
 * marked는 한글과 조합된 볼드 마커를 제대로 처리하지 못하는 경우가 있다:
 * 1. ** 텍스트** (여는 ** 뒤 공백) → 볼드 미인식
 * 2. **텍스트 ** (닫는 ** 앞 공백) → 볼드 미인식
 * 3. **텍스트**한글 (닫는 ** 뒤 한글) → 볼드 미인식
 */
function preprocess(text: string): string {
  // Fix 1: ** 텍스트** → **텍스트**
  text = text.replace(/\*\*\s+([^*]+?)\s*\*\*/g, '**$1**');
  // Fix 2: **텍스트 ** → **텍스트**
  text = text.replace(/\*\*([^*]+?)\s+\*\*/g, '**$1**');
  // Fix 3: **텍스트**한글 → **텍스트** 한글
  text = text.replace(/\*\*([^*]+)\*\*(?=[가-힣])/g, '**$1** ');
  // Fix 4: ---** or ---\n** → ---\n\n** (ensure hr and bold are separate blocks)
  text = text.replace(/---\s*\*\*/g, '---\n\n**');
  return text;
}

export function renderMarkdown(text: string): string {
  if (!text) return '';
  return marked.parse(preprocess(text), { async: false }) as string;
}
