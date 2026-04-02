import re


def extract_cross_references(law_name: str, text: str) -> dict[str, list[str]]:
    """조문 텍스트에서 다른 조문 참조를 추출한다."""
    refs: dict[str, list[str]] = {}
    current_article = None

    for line in text.split("\n"):
        article_match = re.match(r"^#+\s*(제\d+조(?:의\d+)?)", line)
        if article_match:
            current_article = f"{law_name}__{article_match.group(1)}"
            refs[current_article] = []

        if current_article:
            ref_matches = re.findall(r"제(\d+)조(?:의(\d+))?", line)
            for num, sub in ref_matches:
                ref_name = f"{law_name}__제{num}조"
                if sub:
                    ref_name += f"의{sub}"
                if ref_name != current_article and ref_name not in refs[current_article]:
                    refs[current_article].append(ref_name)

    return refs
