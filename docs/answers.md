# The 20 classic answers

The original Magic 8 Ball (Mattel / Ideal, 1970s on) has a 20-sided die with
these answers. This list is the **fixed answer set**. The ball must show
exactly one of these strings, as written here. Do not add, remove or change
answers without an ADR.

There are 10 affirmative, 5 non-committal and 5 negative answers.

| # | Key | Answer | Group |
| --- | --- | --- | --- |
| 1 | `it_is_certain` | It is certain. | affirmative |
| 2 | `it_is_decidedly_so` | It is decidedly so. | affirmative |
| 3 | `without_a_doubt` | Without a doubt. | affirmative |
| 4 | `yes_definitely` | Yes definitely. | affirmative |
| 5 | `you_may_rely_on_it` | You may rely on it. | affirmative |
| 6 | `as_i_see_it_yes` | As I see it, yes. | affirmative |
| 7 | `most_likely` | Most likely. | affirmative |
| 8 | `outlook_good` | Outlook good. | affirmative |
| 9 | `yes` | Yes. | affirmative |
| 10 | `signs_point_to_yes` | Signs point to yes. | affirmative |
| 11 | `reply_hazy_try_again` | Reply hazy, try again. | non-committal |
| 12 | `ask_again_later` | Ask again later. | non-committal |
| 13 | `better_not_tell_you_now` | Better not tell you now. | non-committal |
| 14 | `cannot_predict_now` | Cannot predict now. | non-committal |
| 15 | `concentrate_and_ask_again` | Concentrate and ask again. | non-committal |
| 16 | `dont_count_on_it` | Don't count on it. | negative |
| 17 | `my_reply_is_no` | My reply is no. | negative |
| 18 | `my_sources_say_no` | My sources say no. | negative |
| 19 | `outlook_not_so_good` | Outlook not so good. | negative |
| 20 | `very_doubtful` | Very doubtful. | negative |

## Notes

- The keys are stable IDs. Use them as the option names in decision-model
  requests (`criteria` keys) and in tests.
- The answer text is what the user sees. Keep the punctuation.
- Laya's docs say to take care above about 20 options at default settings.
  20 options is at that limit. See
  [decision-models.md](decision-models.md).
