import re

# A list item starts with a bullet (•) or a dash (-, –) followed by a space.
BULLET_PATTERN = r"(?:^|\s)[•\-–]\s+"

# Words that typically start a new learning outcome inside a
# comma-separated sentence:
#   - infinitives:   razumjeti, koristiti, implementirati, izvršiti, ...
#   - verbal nouns:  razumijevanje, prepoznavanje, korištenje, kreiranje, ...
#   - a few nouns that FIT uses to start an outcome
ACTION_START = re.compile(
    r"^(?:te\s+)?(?:"
    r"[a-zčćžšđ]{3,}(?:ati|eti|iti|uti)"
    r"|[a-zčćžšđ]+nje"
    r"|sposobnost|primjena|implementacija|izrada|analiza|upotreba"
    r")\b"
)

# Present-tense verbs after 'da' (e.g. 'osposobljen da definiše ...,
# objasni ..., analizira ...') end in one of these letters.
PRESENT_VERB = re.compile(r"^[a-zčćžšđ]{2,}(?:e|i|a|uje|ira|še|je)$")
NOT_A_VERB = {
    "i", "a", "te", "kao", "koji", "koje", "kojima", "kojih", "koja", "što",
    "sa", "s", "u", "na", "za", "od", "do", "bez", "iz", "pri", "po",
    "kroz", "uz", "tokom", "sve",
}


def clean(text):
    return re.sub(r"\s+", " ", text).strip(" .,;")


def split_sentences(text):
    """Split at '.', '!', '?' or ':' followed by a capital letter."""
    parts = re.split(r"(?<=[.!?:])\s+(?=[A-ZČĆŽŠĐ])", text.strip())
    return [p.strip() for p in parts if p.strip()]


def split_comma_clauses(sentence):
    """
    Split one sentence into outcomes at commas, but only when at least
    two comma-separated clauses start with an action word or a capital
    letter. Clauses that do not start a new outcome are attached to the
    previous one, so no text is lost.
    """
    # Remove a short leading label such as 'Ishodi učenja:' or 'Student:'
    sentence = re.sub(r"^[^:]{1,40}:\s+", "", sentence)

    clauses = [c.strip() for c in re.split(r",\s+", sentence) if c.strip()]

    def starts_outcome(clause):
        return bool(ACTION_START.match(clause.lower())) or clause[:1].isupper()

    if sum(starts_outcome(c) for c in clauses[1:]) + 1 < 2:
        return [sentence]

    outcomes = []
    for clause in clauses:
        if outcomes and not starts_outcome(clause):
            outcomes[-1] += ", " + clause
        else:
            outcomes.append(re.sub(r"^te\s+", "", clause))
    return outcomes


def starts_with_present_verb(clause):
    """True if a clause starts with a present-tense verb (adverbs skipped)."""
    clause = re.sub(r"^(?:da|te)\s+", "", clause)
    for word in clause.split()[:3]:
        word = word.lower().strip("(),")
        # skip adverbs/adjectives before the verb: 'matematički korektno definiše'
        if word.endswith(("ski", "čki", "no", "o")):
            continue
        if word in NOT_A_VERB or word.endswith("ći"):
            return False
        return bool(PRESENT_VERB.match(word))
    return False


def split_after_da(sentence):
    """
    '... osposobljen da definiše X, objasni Y, analizira Z ...'
    -> ['definiše X', 'objasni Y', 'analizira Z', ...]
    Used only when at least three clauses after 'da' start with a verb;
    otherwise returns None.
    """
    match = re.search(r"\bda\s+", sentence)
    if not match:
        return None

    clauses = [c.strip() for c in re.split(r",\s+", sentence[match.end():]) if c.strip()]
    flags = [starts_with_present_verb(c) for c in clauses]
    if sum(flags) < 3:
        return None

    outcomes = []
    for clause, is_new in zip(clauses, flags):
        clause = re.sub(r"^(?:da|te)\s+", "", clause)
        if outcomes and not is_new:
            outcomes[-1] += ", " + clause
        else:
            outcomes.append(clause)
    return outcomes


def split_learning_outcomes(text):
    """
    Split a learning-outcomes field into a list of individual outcomes.

    1. List (• or -): each list item is one outcome. Sentences before the
       list are also outcomes (split further after 'da', see 3b), except
       an introductory sentence ending with ':'.
    2. Without a list, the text is processed sentence by sentence.
       An introduction ending with ':' (e.g. 'student će steći sljedeće
       kompetencije:') is removed.
    3. Each sentence is then split:
       a. at semicolons, if it contains ';'
       b. after 'da', if it lists several present-tense verbs
          ('da definiše ..., objasni ..., analizira ...')
       c. into short list items, if it follows a ':' and lists nouns
          ('za: implementaciju, pristup, optimizaciju ...')
       d. at commas, if several clauses start with an action word
          ('razumjeti ..., koristiti ..., implementirati ...')
       e. otherwise the whole sentence is one outcome.
    """
    if not text or not text.strip():
        return []

    text = re.sub(r"\s+", " ", text).strip()

    # Rule 1: list
    parts = re.split(BULLET_PATTERN, " " + text)
    head = parts[0].strip()
    items = [p for p in parts[1:] if p.strip()]
    if items:
        head_outcomes = []
        for sentence in split_sentences(head):
            if sentence.endswith(":"):
                continue
            head_outcomes.extend(split_after_da(sentence) or [sentence])
        return [clean(x) for x in head_outcomes + items if clean(x)]

    # Rules 2 and 3: sentence by sentence
    outcomes = []
    for sentence in split_sentences(text):
        if sentence.endswith(":"):
            continue

        intro = re.match(r"^([^:]{1,150}):\s+(.*)$", sentence)
        body = intro.group(2) if intro else sentence

        # 3a: semicolons
        if ";" in body:
            outcomes.extend(p for p in body.split(";") if p.strip())
            continue

        # 3b: 'da' + several verbs
        after_da = split_after_da(body)
        if after_da:
            outcomes.extend(after_da)
            continue

        # 3c: short noun list after ':'
        if intro:
            clauses = [c.strip() for c in re.split(r",\s+", body)]
            if len(clauses) >= 3 and all(len(c.split()) <= 2 for c in clauses[:-1]):
                last = re.split(r"\s+i\s+", clauses[-1], maxsplit=1)
                outcomes.extend(clauses[:-1] + last)
                continue

        # 3d / 3e: commas with action words, or the whole sentence
        outcomes.extend(split_comma_clauses(body))

    return [clean(x) for x in outcomes if clean(x)]