"""The fixed set of 20 classic answers (docs/answers.md)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Answer:
    key: str
    text: str
    group: str  # "affirmative" | "non-committal" | "negative"


ANSWERS: tuple[Answer, ...] = (
    Answer("it_is_certain", "It is certain.", "affirmative"),
    Answer("it_is_decidedly_so", "It is decidedly so.", "affirmative"),
    Answer("without_a_doubt", "Without a doubt.", "affirmative"),
    Answer("yes_definitely", "Yes definitely.", "affirmative"),
    Answer("you_may_rely_on_it", "You may rely on it.", "affirmative"),
    Answer("as_i_see_it_yes", "As I see it, yes.", "affirmative"),
    Answer("most_likely", "Most likely.", "affirmative"),
    Answer("outlook_good", "Outlook good.", "affirmative"),
    Answer("yes", "Yes.", "affirmative"),
    Answer("signs_point_to_yes", "Signs point to yes.", "affirmative"),
    Answer("reply_hazy_try_again", "Reply hazy, try again.", "non-committal"),
    Answer("ask_again_later", "Ask again later.", "non-committal"),
    Answer("better_not_tell_you_now", "Better not tell you now.", "non-committal"),
    Answer("cannot_predict_now", "Cannot predict now.", "non-committal"),
    Answer("concentrate_and_ask_again", "Concentrate and ask again.", "non-committal"),
    Answer("dont_count_on_it", "Don't count on it.", "negative"),
    Answer("my_reply_is_no", "My reply is no.", "negative"),
    Answer("my_sources_say_no", "My sources say no.", "negative"),
    Answer("outlook_not_so_good", "Outlook not so good.", "negative"),
    Answer("very_doubtful", "Very doubtful.", "negative"),
)

BY_KEY: dict[str, Answer] = {a.key: a for a in ANSWERS}
