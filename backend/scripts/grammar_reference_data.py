#!/usr/bin/env python3
"""
Grammar Reference Data -- CBSE Grade 9 & 10 Communicative Grammar
====================================================================
NCERT/CBSE does not publish a single "Grammar chapter" PDF the way it
does for literature chapters -- grammar is taught through workbook
exercises spread across the school year, following a fixed topic list
that has been stable across CBSE English syllabi for Classes 9-10.

This module provides a hand-written GROUNDING REFERENCE TEXT for each
topic -- the rules, forms, usage patterns, and common errors a
qualified CBSE English teacher would teach. This plays the same role as
CHAPTER_PDF_TEXT in the other prompt pipelines: GPT-5.5 must ground
every rule/example in this reference text, not invent its own rules.

Usage: imported by prepare_gpt55_prompts_grammar.py.
"""

GRADE_9_TOPICS = [
    "Grammar: Tenses",
    "Grammar: Modals",
    "Grammar: Subject-Verb Concord",
    "Grammar: Determiners",
    "Grammar: Reported Speech (Statements and Questions)",
    "Grammar: Commands, Requests and Exclamations in Reported Speech",
    "Grammar: Clauses (Noun, Adjective and Adverb Clauses)",
    "Grammar: Active and Passive Voice",
]

GRADE_10_TOPICS = [
    "Grammar: Tenses (Advanced Usage)",
    "Grammar: Modals (Advanced Usage)",
    "Grammar: Subject-Verb Concord (Advanced Rules)",
    "Grammar: Determiners (Advanced Usage)",
    "Grammar: Reported Speech (All Sentence Types)",
    "Grammar: Clauses and Sentence Transformation",
    "Grammar: Active and Passive Voice (Advanced Usage)",
    "Grammar: Editing and Omission (Error Correction)",
]

REFERENCE_TEXT = {

    "Grammar: Tenses": """
TENSES -- reference for CBSE Grade 9

The tense of a verb shows the time of an action and whether it is
complete, continuing, or repeated.

1. Present Tenses
   - Simple Present: subject + base verb (+s/es for third person
     singular). Used for habitual actions, facts, and general truths.
     Example: "Water boils at 100 degrees Celsius." "She walks to school."
   - Present Continuous: subject + is/am/are + verb-ing. Used for
     actions happening now or temporary ongoing actions.
     Example: "I am reading a book right now."
   - Present Perfect: subject + has/have + past participle. Used for
     actions completed at an unspecified past time, or actions that
     started in the past and continue now.
     Example: "She has finished her homework." "I have lived here for five years."
   - Present Perfect Continuous: subject + has/have + been + verb-ing.
     Used for actions that started in the past and are still continuing.
     Example: "They have been playing football since morning."

2. Past Tenses
   - Simple Past: subject + past form of verb. Used for completed
     actions at a specific past time.
     Example: "He visited his grandmother yesterday."
   - Past Continuous: subject + was/were + verb-ing. Used for an action
     in progress at a particular past time, often interrupted by
     another action.
     Example: "I was watching TV when the phone rang."
   - Past Perfect: subject + had + past participle. Used for an action
     completed before another past action.
     Example: "She had left before I arrived."
   - Past Perfect Continuous: subject + had been + verb-ing. Used for
     an action continuing up to a point in the past.
     Example: "He had been waiting for an hour before the bus came."

3. Future Tenses
   - Simple Future: subject + will/shall + base verb.
     Example: "We will visit the museum tomorrow."
   - Future Continuous: subject + will be + verb-ing.
     Example: "This time next week, I will be travelling."
   - Future Perfect: subject + will have + past participle.
     Example: "By next year, she will have completed her course."
   - Future Perfect Continuous: subject + will have been + verb-ing.
     Example: "By evening, he will have been working for ten hours."

COMMON ERRORS:
- Confusing simple past with present perfect: "I have seen him
  yesterday" is incorrect; it should be "I saw him yesterday" (a
  specific past time requires simple past, not present perfect).
- "since" is used with a point in time, "for" with a duration:
  "since 2015" (point in time) vs "for five years" (duration).
- Forgetting third-person singular -s/-es in simple present:
  "She go to school" is incorrect; correct is "She goes to school."
""",

    "Grammar: Modals": """
MODALS -- reference for CBSE Grade 9

Modal verbs (can, could, may, might, shall, should, will, would, must,
ought to, need, dare) express ability, permission, possibility,
necessity, obligation, or advice. A modal is always followed by the
base form of the main verb (no "to", no -s, no -ing).

1. Ability: can (present), could (past)
   Example: "She can swim well." "He could run fast when he was young."

2. Permission: may, can (informal), could (very polite)
   Example: "May I come in?" "Could you please pass the salt?"

3. Possibility: may, might, could
   "May" suggests a fairly strong possibility; "might" suggests a
   weaker or more hypothetical possibility.
   Example: "It may rain today." "It might rain, but I am not sure."

4. Necessity/Obligation: must, have to
   "Must" often expresses the speaker's own judgement of obligation;
   "have to" often expresses an obligation imposed by an external rule.
   Example: "You must wear a helmet while riding a bike (my advice)."
   "Students have to submit the form by Friday (school rule)."

5. Advice: should, ought to
   Example: "You should apologise to her." "We ought to help others."

6. Absence of necessity: need not, don't have to
   Example: "You need not come if you are unwell."

7. Prohibition: must not, cannot
   Example: "You must not smoke here."

COMMON ERRORS:
- Using "to" after a modal: "She can to sing" is incorrect; correct is
  "She can sing."
- Confusing "must not" (prohibition) with "need not" (absence of
  obligation): "You must not come" means do not come; "You need not
  come" means coming is optional.
- Adding -s to a modal for third person: "He cans swim" is incorrect;
  modals never take -s.
""",

    "Grammar: Subject-Verb Concord": """
SUBJECT-VERB CONCORD (AGREEMENT) -- reference for CBSE Grade 9

The verb in a sentence must agree with its subject in number (singular
or plural) and person (first, second, third).

1. Basic rule: a singular subject takes a singular verb; a plural
   subject takes a plural verb.
   Example: "The boy plays football." "The boys play football."

2. Subjects joined by "and" usually take a plural verb.
   Example: "Rahul and Priya are good friends."
   Exception: when the two nouns joined by "and" refer to a single
   idea or entity, the verb is singular.
   Example: "Bread and butter is my favourite breakfast."

3. Subjects joined by "or"/"nor" take a verb that agrees with the
   nearer subject.
   Example: "Neither the teacher nor the students were present."
   Example: "Either she or I am responsible."

4. Collective nouns (team, family, class, committee) take a singular
   verb when acting as one unit, and a plural verb when members are
   considered individually.
   Example: "The team is playing well (as a unit)."
   Example: "The team are arguing among themselves (individuals)."

5. Indefinite pronouns such as each, either, neither, everyone,
   someone, nobody are always singular.
   Example: "Each of the students has submitted the assignment."

6. A phrase between the subject and the verb does not change the
   verb's number; the verb still agrees with the true subject.
   Example: "The list of items is on the table" (subject is "list",
   not "items").

COMMON ERRORS:
- "The list of items are ready" is incorrect; correct is "The list of
  items is ready" (agreement with "list", not "items").
- "Neither of them are correct" is incorrect; correct is "Neither of
  them is correct" ("neither" is singular).
- "Everyone have finished" is incorrect; correct is "Everyone has
  finished" ("everyone" is singular).
""",

    "Grammar: Determiners": """
DETERMINERS -- reference for CBSE Grade 9

Determiners are words placed before nouns to specify quantity,
possession, or definiteness. Common categories: articles (a, an, the),
demonstratives (this, that, these, those), possessives (my, your, his,
her, its, our, their), quantifiers (some, any, much, many, few, little,
each, every, all, both, several), and numbers (one, two, first, second).

1. Articles
   - "a"/"an" (indefinite): used before a noun mentioned for the first
     time or not specific; "a" before consonant sounds, "an" before
     vowel sounds. Example: "a book", "an apple", "a university"
     (sounds like "yoo").
   - "the" (definite): used before a specific noun already known to
     speaker and listener. Example: "The book on the table is mine."

2. Demonstratives: this/these (near), that/those (far); agree in
   number with the noun. Example: "This pen is mine; those pens are
   yours."

3. Quantifiers with countable vs uncountable nouns:
   - "many", "few", "several" go with countable nouns (many books).
   - "much", "little" go with uncountable nouns (much water, little
     time).
   - "some"/"any": "some" in affirmative sentences, "any" in negative
     sentences and questions. Example: "I have some milk." "I don't
     have any milk." "Do you have any milk?"

4. "each" vs "every": "each" emphasises individual items in a small,
   specific group; "every" emphasises the group as a whole, usually
   larger or more general. Both take a singular verb.

COMMON ERRORS:
- "many water" is incorrect (water is uncountable); correct is "much
  water".
- "a university" is often wrongly written as "an university"; the "u"
  in university sounds like "yoo" (a consonant sound), so "a" is
  correct.
- Omitting "the" before a superlative: "He is best student" is
  incorrect; correct is "He is the best student."
""",

    "Grammar: Reported Speech (Statements and Questions)": """
REPORTED SPEECH: STATEMENTS AND QUESTIONS -- reference for CBSE Grade 9

Reported (indirect) speech reports what someone said without quoting
their exact words. Converting direct speech to reported speech usually
requires changes in tense, pronouns, and time/place expressions.

1. Reporting statements
   - If the reporting verb is in the past tense (said, told), the tense
     in the reported clause usually shifts one step back (backshift):
     simple present -> simple past; present continuous -> past
     continuous; present perfect -> past perfect; simple past -> past
     perfect (often); will -> would; can -> could; may -> might; must
     -> had to.
     Example: Direct: "I am happy," she said.
     Reported: She said that she was happy.
     Example: Direct: He said, "I will come tomorrow."
     Reported: He said that he would come the next day.

2. Pronoun changes: first person in direct speech usually becomes
   third person in reported speech, matching the subject who is being
   reported.
   Example: Direct: "I have finished my work," said Ravi.
   Reported: Ravi said that he had finished his work.

3. Time and place word changes (common set):
   now -> then; today -> that day; tomorrow -> the next day / the
   following day; yesterday -> the day before / the previous day;
   here -> there; this -> that; these -> those; ago -> before.

4. Reporting Yes/No questions: use "if" or "whether" and change to
   statement word order (no auxiliary at the start).
   Example: Direct: He asked, "Are you coming?"
   Reported: He asked if I was coming.

5. Reporting Wh-questions: keep the question word, remove the
   auxiliary-first order, use statement word order.
   Example: Direct: She asked, "Where do you live?"
   Reported: She asked where I lived.

COMMON ERRORS:
- Keeping question word order in reported questions: "He asked where
  do I live" is incorrect; correct is "He asked where I lived."
- Forgetting to backshift the tense: "She said she is happy" (when the
  reporting verb is in the past) should usually be "She said she was
  happy."
- Missing "if"/"whether" in reported Yes/No questions: "He asked I was
  coming" is incorrect; correct is "He asked if I was coming."
""",

    "Grammar: Commands, Requests and Exclamations in Reported Speech": """
REPORTED SPEECH: COMMANDS, REQUESTS AND EXCLAMATIONS -- CBSE Grade 9

1. Reporting commands and orders: use "told" + object + "to" +
   base verb (infinitive). The reporting verb changes from "said" to
   "told" (or "ordered", "commanded").
   Example: Direct: "Close the door," he said.
   Reported: He told me to close the door.

2. Reporting negative commands: use "told...not to" + base verb.
   Example: Direct: "Don't touch that wire," she said.
   Reported: She told him not to touch that wire.

3. Reporting requests: use "requested"/"asked" + object + "to" + base
   verb; polite words like "please" are dropped, replaced by the
   reporting verb "requested".
   Example: Direct: "Please help me," she said.
   Reported: She requested him to help her.

4. Reporting exclamations: the reporting verb becomes "exclaimed with
   joy/sorrow/surprise" etc., and the exclamatory sentence is
   converted into a statement introduced by "that".
   Example: Direct: "What a beautiful painting!" she said.
   Reported: She exclaimed with joy that it was a very beautiful
   painting.
   Example: Direct: "Alas! I have lost my purse," he said.
   Reported: He exclaimed with sorrow that he had lost his purse.

5. Reporting wishes/greetings: use "wished" + object + noun form of
   the greeting.
   Example: Direct: "Good morning," she said.
   Reported: She wished him good morning.

COMMON ERRORS:
- Keeping the imperative form in reported speech: "He told me close
  the door" is incorrect; correct is "He told me to close the door."
- Forgetting "not" placement in negative commands: "He told me to not
  touch it" is less standard; the more standard form is "He told me
  not to touch it."
- Using "said" instead of "told" when there is an object being
  addressed: "He said me to come" is incorrect; correct is "He told me
  to come."
""",

    "Grammar: Clauses (Noun, Adjective and Adverb Clauses)": """
CLAUSES -- reference for CBSE Grade 9

A clause is a group of words containing a subject and a verb. An
independent (main) clause can stand alone as a sentence; a dependent
(subordinate) clause cannot stand alone and depends on a main clause.

1. Noun Clause: functions as a noun (subject, object, or complement)
   in a sentence, usually beginning with that, what, why, how, if,
   whether, who, etc.
   Example: "That he is honest is well known." (subject)
   Example: "I know that he is honest." (object)
   Example: "The truth is that he was late." (complement)

2. Adjective Clause (Relative Clause): functions as an adjective,
   describing a noun, usually beginning with who, whom, whose, which,
   that, where, when.
   Example: "The man who helped me is my neighbour."
   Example: "This is the house where I was born."

3. Adverb Clause: functions as an adverb, modifying the verb and
   showing time, place, reason, condition, purpose, or contrast,
   usually beginning with when, while, because, if, although, so
   that, as soon as, etc.
   Example: "He left before the meeting started." (time)
   Example: "Although it was raining, we went out." (contrast)
   Example: "She studied hard so that she could pass." (purpose)

COMMON ERRORS:
- Confusing a noun clause with an adjective clause: in "The book that
  I bought is interesting," "that I bought" describes "book" (an
  adjective clause), not a noun clause.
- Missing the subordinating word: "He said he honest" is incorrect;
  correct is "He said that he was honest."
- Comma splices between two independent clauses: "It was raining, we
  stayed inside" should use a conjunction or subordinate clause: "It
  was raining, so we stayed inside," or "Because it was raining, we
  stayed inside."
""",

    "Grammar: Active and Passive Voice": """
ACTIVE AND PASSIVE VOICE -- reference for CBSE Grade 9

Voice shows whether the subject of a sentence performs the action
(active) or receives the action (passive).

1. Active voice: subject + verb + object.
   Example: "The chef cooks the meal."

2. Passive voice: object of the active sentence becomes the subject +
   a form of "be" + past participle + (by + agent, optional).
   Example: "The meal is cooked by the chef."

3. Converting active to passive by tense:
   - Simple present: is/am/are + past participle.
     "She writes a letter." -> "A letter is written by her."
   - Simple past: was/were + past participle.
     "She wrote a letter." -> "A letter was written by her."
   - Present continuous: is/am/are + being + past participle.
     "She is writing a letter." -> "A letter is being written by her."
   - Present perfect: has/have + been + past participle.
     "She has written a letter." -> "A letter has been written by her."
   - Modals: modal + be + past participle.
     "She can write a letter." -> "A letter can be written by her."

4. When there is no clear agent, "by + agent" is often omitted.
   Example: "English is spoken all over the world."

5. Only transitive verbs (verbs that take a direct object) can be
   changed into the passive voice; intransitive verbs (e.g. sleep,
   arrive) cannot.

COMMON ERRORS:
- Forgetting to change the verb form: "A letter is write by her" is
  incorrect; correct is "A letter is written by her."
- Using the wrong tense of "be": "A letter is written by her
  yesterday" is incorrect (mixing present "is" with past time
  "yesterday"); correct is "A letter was written by her yesterday."
- Trying to passivise an intransitive verb: "Is slept by him" is
  incorrect; "sleep" has no object and cannot be made passive.
""",

    "Grammar: Tenses (Advanced Usage)": """
TENSES -- ADVANCED USAGE -- reference for CBSE Grade 10

Builds on Grade 9 tense forms with more complex, mixed-tense sentences
and conditional/time-clause combinations typical of Grade 10 exam
patterns (error correction, sentence completion, and dialogue writing).

1. Mixed tense sentences: a single sentence may combine two different
   tenses correctly when describing two related but distinct events.
   Example: "By the time he arrives, we will have finished dinner."
   (future perfect + simple present in the time clause)

2. Time clauses with "when", "while", "as soon as", "until", "before",
   "after" do NOT use "will" for future time; they use simple present
   even though the overall meaning is future.
   Example: "I will call you when I reach home" (not "when I will
   reach home").

3. Reported speech backshift combined with conditional sentences:
   Direct: "If I study, I will pass." -> Reported: "She said that if
   she studied, she would pass." (both clauses shift together)

4. Present tense used for definite future arrangements/schedules:
   Example: "The train leaves at 6 p.m. tomorrow."

COMMON ERRORS:
- Using "will" inside a time clause: "When I will reach home, I will
  call you" is incorrect; correct is "When I reach home, I will call
  you."
- Mismatched tense across a sentence describing sequential events:
  "He finished his work after he will eat" is incorrect; correct is
  "He finished his work after he had eaten" or similar sequencing.
""",

    "Grammar: Modals (Advanced Usage)": """
MODALS -- ADVANCED USAGE -- reference for CBSE Grade 10

1. Modals of deduction/probability in the past: must have + past
   participle (strong certainty); might have/could have + past
   participle (possibility); can't have + past participle (near
   certainty that something did NOT happen).
   Example: "She must have left already; her car is gone."
   Example: "He might have missed the bus."
   Example: "He can't have finished so quickly; it's only been five
   minutes."

2. "Should have"/"ought to have" + past participle: express regret or
   criticism about something that did not happen but was expected.
   Example: "You should have told me earlier."

3. "Needn't have" + past participle: an unnecessary action that was
   actually done.
   Example: "You needn't have brought an umbrella; it didn't rain."

4. Modals in reported speech: will->would, can->could, may->might,
   must (obligation)->had to, must (deduction)->must (unchanged).

COMMON ERRORS:
- Confusing "must have" (deduction) with "had to" (past obligation):
  "He must have gone to school yesterday" (deduction) is different
  from "He had to go to school yesterday" (obligation).
- "Should have went" is incorrect; correct is "should have gone" (past
  participle, not simple past, after "have").
""",

    "Grammar: Subject-Verb Concord (Advanced Rules)": """
SUBJECT-VERB CONCORD -- ADVANCED RULES -- reference for CBSE Grade 10

1. Subjects that look plural but are singular in meaning (e.g. news,
   mathematics, physics, athletics) take a singular verb.
   Example: "The news is disturbing." "Mathematics is my favourite
   subject."

2. "A number of" + plural noun takes a plural verb; "the number of" +
   plural noun takes a singular verb.
   Example: "A number of students are absent." "The number of absent
   students is high."

3. Fractions/percentages: verb agrees with the noun that follows "of".
   Example: "Half of the cake is gone." "Half of the students are
   present."

4. Relative pronoun clauses: the verb in the relative clause agrees
   with the noun the pronoun refers to.
   Example: "He is one of the students who study hard" (study agrees
   with "students," plural, since "who" refers to the whole group of
   students of which he is one). Some CBSE answer keys also accept
   "studies" depending on context; teachers should apply the standard
   rule taught in the textbook.

COMMON ERRORS:
- "The number of students are increasing" is incorrect; correct is
  "The number of students is increasing" ("the number" is singular).
- "Physics are difficult" is incorrect; correct is "Physics is
  difficult" (subject name ending in -s but singular in meaning).
""",

    "Grammar: Determiners (Advanced Usage)": """
DETERMINERS -- ADVANCED USAGE -- reference for CBSE Grade 10

1. "a few"/"few" and "a little"/"little": "a few"/"a little" have a
   positive sense (some, a small but sufficient amount); "few"/"little"
   (without "a") have a negative sense (almost none, not enough).
   Example: "I have a few friends here" (positive - I do have some).
   Example: "I have few friends here" (negative - almost no friends).

2. "the" with superlatives, ordinal numbers, and unique nouns:
   Example: "the first day", "the sun", "the Ganga".

3. "no" vs "not any": "no" can be used as a determiner directly before
   a noun without needing "not"; "not any" requires the verb to already
   be negative.
   Example: "There is no water left." = "There isn't any water left."

4. Zero article with general/abstract plural or uncountable nouns:
   Example: "Honesty is the best policy." "Dogs are loyal animals."
   (no article before general/abstract nouns)

COMMON ERRORS:
- "I have little friends, so I am happy" is a common error; if the
  intended meaning is positive, "a little"/"a few" should be used
  instead of "little"/"few".
- Adding "the" before general/abstract nouns: "The honesty is
  important" is incorrect; correct is "Honesty is important."
""",

    "Grammar: Reported Speech (All Sentence Types)": """
REPORTED SPEECH -- ALL SENTENCE TYPES -- reference for CBSE Grade 10

Grade 10 combines all sentence types (statements, questions, commands,
requests, exclamations) into single mixed passages/dialogues, testing
the complete backshift + pronoun + time/place system fluently.

1. Mixed-dialogue conversion: a short conversation with multiple
   speakers and sentence types must be converted while keeping each
   speaker's reporting verb, tense shift, and pronoun changes
   consistent throughout the passage.

2. Reporting a question that also contains a request:
   Example: Direct: "Could you please tell me the time?" she asked.
   Reported: She politely asked him to tell her the time. / She asked
   if he could tell her the time.

3. Reporting conditional sentences: both the "if" clause and the main
   clause shift tense together (see Tenses Advanced Usage above).

4. Reporting speech containing modals of deduction: modals of pure
   deduction (must, might, could for probability) usually remain
   UNCHANGED in reported speech, since they still express a present
   deduction about a situation.
   Example: Direct: "He must be at home," she said.
   Reported: She said that he must be at home.

COMMON ERRORS:
- Mixing tenses inconsistently across a longer reported passage (some
  sentences backshifted, others not) -- the whole passage must follow
  one consistent shift once the reporting verb sets the past-tense
  frame.
- Reporting a command as a statement: dropping the "to + infinitive"
  structure for an imperative sentence.
""",

    "Grammar: Clauses and Sentence Transformation": """
CLAUSES AND SENTENCE TRANSFORMATION -- reference for CBSE Grade 10

Grade 10 tests the ability to combine simple sentences into complex or
compound sentences using clauses, and to transform one sentence type
into another with the same meaning.

1. Combining simple sentences into a complex sentence using a clause:
   Example: Simple: "He is honest. Everyone respects him."
   Complex: "Everyone respects him because he is honest." (adverb
   clause of reason)

2. Combining simple sentences into a compound sentence using a
   coordinating conjunction (and, but, or, so, yet):
   Example: "He worked hard, so he succeeded."

3. Transforming a complex sentence into a simple sentence by reducing
   a clause to a phrase:
   Example: Complex: "Although he was tired, he finished the work."
   Simple: "In spite of being tired, he finished the work."

4. Transforming degrees of comparison (positive/comparative/
   superlative) while keeping the meaning the same:
   Example: "No other boy in the class is as tall as Ravi." = "Ravi is
   the tallest boy in the class."

5. Transforming assertive sentences into interrogative or exclamatory
   sentences with the same meaning:
   Example: Assertive: "It was a beautiful sight." Exclamatory: "What
   a beautiful sight it was!"

COMMON ERRORS:
- Losing the original meaning when reducing a clause to a phrase
  (e.g. changing the logical relationship from reason to contrast by
  mistake).
- Incorrect comparative/superlative transformation: "Ravi is taller
  than any boy in the class" is a common near-miss; the precise
  standard form is "Ravi is taller than any other boy in the class."
""",

    "Grammar: Active and Passive Voice (Advanced Usage)": """
ACTIVE AND PASSIVE VOICE -- ADVANCED USAGE -- reference for CBSE Grade 10

1. Passive voice with modals in the past: modal + have been + past
   participle.
   Example: "The work should have been finished by now."

2. Passive of sentences with two objects (indirect and direct object):
   either object can become the subject of the passive sentence,
   though making the indirect (person) object the subject is more
   common and natural.
   Example: "She gave him a book." -> "He was given a book by her." OR
   "A book was given to him by her."

3. Passive of imperative sentences: use "Let" + object + "be" + past
   participle.
   Example: "Close the door." -> "Let the door be closed."

4. Passive with verbs followed by an infinitive (make, let, help):
   "make" changes to "be made to" in the passive.
   Example: "They made him work." -> "He was made to work."

5. Passive of reporting verbs in indirect speech (used for formal or
   impersonal statements): "It is said that..." / "He is said to
   have..."
   Example: "People say he is honest." -> "It is said that he is
   honest." / "He is said to be honest."

COMMON ERRORS:
- Forgetting "to" after "made" in the passive: "He was made work" is
  incorrect; correct is "He was made to work."
- Incorrect passive of an imperative: "The door is closed" (simple
  passive statement) is not the same as the passive IMPERATIVE "Let
  the door be closed" -- students often confuse the two.
""",

    "Grammar: Editing and Omission (Error Correction)": """
EDITING AND OMISSION -- reference for CBSE Grade 10

CBSE Grade 10 includes a dedicated "editing and omission" question type
in the exam (Writing and Grammar section), testing the ability to spot
a single incorrect or missing word per line and supply the correction.

1. Editing: a short passage is given with one grammatical error per
   line (marked by underlining or a blank). The student identifies the
   incorrect word and writes the correct word.
   Common error types tested: wrong tense form, wrong article, wrong
   preposition, wrong subject-verb agreement, wrong degree of
   comparison, wrong modal.
   Example: Incorrect: "She is went to school." Correct word: "gone"
   (or restructure to "She has gone to school" depending on the exact
   exam format used).

2. Omission: a short passage has one word omitted per line (usually a
   determiner, preposition, auxiliary verb, or conjunction) marked
   with a caret (^). The student must identify the missing word and
   its correct position.
   Example: "He went ^ market." Missing word: "to" (preposition).
   Example: "I ^ happy today." Missing word: "am" (auxiliary verb).

3. Standard answer format for both editing and omission exercises:
   present the answer as: Incorrect word / Missing word marked by a
   caret -> Correct word, exactly as required by the CBSE answer-key
   format, so that answers are directly usable for exam practice.

4. Categories of words most frequently tested for omission: articles
   (a, an, the), prepositions (in, on, at, to, of, with), auxiliary
   verbs (is, am, are, was, were, has, have, had, will, would),
   conjunctions (and, but, or, because).

COMMON ERRORS (student mistakes when attempting these exercises):
- Providing a full sentence rewrite instead of just the single
  incorrect/missing word, which does not match the CBSE exam format.
- Confusing which word is "incorrect" vs which word is "missing" --
  editing exercises have a WRONG word to replace; omission exercises
  have a MISSING word to insert; these are two different question
  types and must not be mixed up.
- Missing the exact caret position for the omitted word in the answer.
""",

}
