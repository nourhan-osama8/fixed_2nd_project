"""
Classifies a transcribed Arabic customer response into YES / NO / UNKNOWN.

Deliberately keyword/phrase-based for Egyptian and Modern Standard Arabic.
Handles negations (e.g., "مش شغال", "ومش شغالة" classified as NO),
uncertainty phrases (e.g., "مش عارف", "مش متأكد" as UNKNOWN),
attached Arabic conjunctions (e.g., "ومش", "ولسه"),
and word-boundary checks to prevent false positives (e.g., "مشكلة" doesn't match "مش").
"""
import re
from app.core.constants import FollowupResult


def normalize_arabic(text: str) -> str:
    """
    Normalizes Egyptian and Modern Standard Arabic text:
    - Normalizes Alef variants (أ, إ, آ -> ا)
    - Normalizes Lam-Alef with hamza (لأ, لإ, لآ -> لا)
    - Normalizes Taa Marbuta (ة -> ه)
    - Normalizes Alef Maksura (ى -> ي)
    - Separates attached conjunctions (e.g., و/ف on particles: و某个 -> و 某个)
    - Strips tashkeel and punctuation
    """
    if not text:
        return ""
    t = text.strip().lower()
    t = re.sub(r"[\u064B-\u065F\u0670]", "", t)  # Tashkeel
    t = re.sub(r"[إأآا]", "ا", t)
    t = re.sub(r"ل[أإآا]", "لا", t)
    t = re.sub(r"ة", "ه", t)
    t = re.sub(r"ى", "ي", t)
    t = re.sub(r"[.,!؟?؛:\-_/\\()\[\]{}'\"`~^]", " ", t)
    # Separate attached prefix waw/faa before common particles
    t = re.sub(r"(?<!\w)[وف](مش|لا|لسه|ايوه|اه|تمام|كويس)(?!\w)", r" \1", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


RAW_YES = [
    "ايوه", "ايوا", "نعم", "تمام", "اتحلت", "اتحل",
    "حلت", "خلصت", "كويس", "كويسه", "شغال", "شغاله", "تم",
    "اه", "ماشي", "ok", "okay", "مظبوط", "تمام التمام", "محلوله", "اتصلحت", "صلحت",
]

RAW_NO = [
    "لا", "مش", "لسه", "برضو", "برضه", "موجوده", "موجود",
    "مفيش فايده", "زي ما هي", "مش شغال", "مش شغاله", "عطلانه", "واقفه",
    "ما اتحلتش", "ما اتحلت", "ما اتحل", "باظت", "خربانه", "ما اشتغلتش", "خربت",
]

RAW_NEGATED = [
    "مش شغال", "مش شغاله", "مش تمام", "مش كويس", "مش كويسه",
    "مش اوكي", "ما اتحلت", "ما اتحلتش", "ما اتحل",
    "غير شغال", "غير شغاله", "غير تمام", "مش محلول", "مش محلوله",
    "ما اشتغلتش", "ما اشتغل", "مش مظبوط", "مش اوكي",
]

RAW_UNCERTAIN = [
    "مش عارف", "مش عارفه", "مش متاكد", "مش متاكده", "مش فاهم", "مش فاهمه",
    "مش فاكر", "مش متذكر", "مش واضح", "مش باين", "مش متاكدين",
    "ممكن", "يمكن", "الله اعلم", "معرفش", "ما اعرفش", "ماعرفش",
]

YES_KEYWORDS = [normalize_arabic(k) for k in RAW_YES]
NO_KEYWORDS = [normalize_arabic(k) for k in RAW_NO]
NEGATED_POSITIVES = [normalize_arabic(k) for k in RAW_NEGATED]
UNCERTAIN_PHRASES = [normalize_arabic(k) for k in RAW_UNCERTAIN]


def _match_phrase(text: str, phrase: str) -> bool:
    """Matches exact word or phrase boundary to avoid substring collisions."""
    tokens = [re.escape(tok) for tok in phrase.split()]
    pattern = r"(?<!\w)" + r"\s+".join(tokens) + r"(?!\w)"
    return bool(re.search(pattern, text, re.UNICODE))


def classify_response(speech_text: str) -> FollowupResult:
    """
    Classifies a raw transcript or text into YES, NO, or UNKNOWN.
    """
    if not speech_text or not speech_text.strip():
        return FollowupResult.UNKNOWN

    norm = normalize_arabic(speech_text)

    # 1. Check if customer expresses uncertainty
    if any(_match_phrase(norm, p) for p in UNCERTAIN_PHRASES):
        return FollowupResult.UNKNOWN

    # 2. Check for negated positive phrases (e.g. "مش شغال", "ما اتحلتش")
    has_negated = any(_match_phrase(norm, phrase) for phrase in NEGATED_POSITIVES)

    # 3. Mask out negated positive phrases before checking YES keywords
    text_for_yes = norm
    for phrase in NEGATED_POSITIVES:
        tokens = [re.escape(tok) for tok in phrase.split()]
        pattern = r"(?<!\w)" + r"\s+".join(tokens) + r"(?!\w)"
        text_for_yes = re.sub(pattern, " ", text_for_yes, flags=re.UNICODE)

    has_no = any(_match_phrase(norm, k) for k in NO_KEYWORDS) or has_negated
    has_yes = any(_match_phrase(text_for_yes, k) for k in YES_KEYWORDS)

    if has_no and not has_yes:
        return FollowupResult.NO
    if has_yes and not has_no:
        return FollowupResult.YES

    # Both matched (ambiguous/contradictory phrase) or neither matched
    return FollowupResult.UNKNOWN