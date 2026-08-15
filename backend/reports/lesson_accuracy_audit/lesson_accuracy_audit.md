# Comprehensive Lesson Content Accuracy Audit
_Generated: 2026-08-12 15:25 UTC_

Reads all 5 lesson_cache steps per chapter against that chapter's RAG-sourced textbook text, using the admin-configured LLM to fact-check line by line: unsupported claims, fabricated numbers, arithmetic errors, topic mismatches, and cross-step inconsistencies.

## Summary
| Metric | Count |
|---|---|
| Chapters audited | 803 |
| Chapters with zero flagged issues | 11 |
| Chapters that errored (could not audit) | 11 |
| 🔴 High severity issues | 559 |
| 🟠 Medium severity issues | 29 |
| ⚪ Low severity issues | 2785 |
| **Total issues** | **3373** |

---

## High severity issues

### Grade 10 / English / Chapter 2: Nelson Mandela: Long Walk to Freedom — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Noun formation: Formation comes from form, government from govern, rebellion from rebel, and constitution from constitute;"
- **Problem:** This section appears to be about language exercises and vocabulary, which is not the main focus of the chapter.

### Grade 10 / English / Chapter 3: Two Stories about Flying — Exam-style problems
- **Type:** UNSUPPORTED_CLAIM
- **Quote:** "The control centre reports that no second aeroplane was in the sky or on radar, and the helper disappears."
- **Problem:** This contradicts the narrator's experience of seeing the pilot and following the black aeroplane.

### Grade 10 / English / Chapter 5: Glimpses of India — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will study Coorg's river, wildlife, adventure activities, viewpoints, and travel information."
- **Problem:** This step's content is about Coorg, but the chapter label is Chapter 5: Glimpses of India, which is about Goan paders and their culture.

### Grade 10 / English / Chapter 5: Glimpses of India — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will study the journey in Tea from Assam, the legends and history associated with tea, and the view of the Dhekiabari estate."
- **Problem:** This step's content is about Assam tea, but the chapter label is Chapter 5: Glimpses of India, which is about Goan paders and their culture.

### Grade 10 / English / Chapter 5: Glimpses of India — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will explore Coorg's location, climate, landscape, people, and cultural traditions."
- **Problem:** This step's content is about Coorg, but the chapter label is Chapter 5: Glimpses of India, which is about Goan paders and their culture.

### Grade 10 / English / Grammar: Clauses and Sentence Transformation — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will learn to combine simple sentences into a compound sentence."
- **Problem:** This step is about compound sentences, but the chapter label is about complex sentences.

### Grade 10 / English / Grammar: Clauses and Sentence Transformation — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will learn to transform positive, comparative, and superlative degrees."
- **Problem:** This step is about degree transformation, but the chapter label is about clauses and sentence transformation.

### Grade 10 / English / Grammar: Clauses and Sentence Transformation — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will learn to transform assertive sentences into interrogative or exclamatory forms."
- **Problem:** This step is about sentence transformation, but the chapter label is about clauses and sentence transformation.

### Grade 10 / English / Grammar: Clauses and Sentence Transformation — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will learn to change a complex sentence into a simple sentence."
- **Problem:** This step is about reducing complex sentences to simple sentences, but the chapter label is about clauses and sentence transformation.

### Grade 10 / English / Supplementary Reader - Chapter 1: A Triumph of Surgery — Exam preparation
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, you will learn how to convert direct speech into reported speech, especially focusing on sentences where children are speaking about their feelings, health, or experiences."
- **Problem:** This step is about reported speech, which is a different topic from the chapter 'A Triumph of Surgery'.

### Grade 10 / English / Supplementary Reader - Chapter 1: A Triumph of Surgery — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "Today, we will learn how to identify and correct common grammatical errors in sentences, especially focusing on sentence structure, verb forms, and word usage."
- **Problem:** This step is about common errors in sentence construction, which is a different topic from the chapter 'A Triumph of Surgery'.

### Grade 10 / English / Supplementary Reader - Chapter 2: The Thief's Story — Core explanation
- **Type:** ARITHMETIC_ERROR
- **Quote:** "So, Hari Singh has 12 notes of 50 rupees each."
- **Problem:** The calculation is incorrect. 600 ÷ 50 = 12, but the problem states that each note is worth 50 rupees, which is correct, but the total amount is 600, not 12 notes.

### Grade 10 / English / Supplementary Reader - Chapter 4: A Question of Trust — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "Preparing for exams involves understanding the story thoroughly, practicing different types of questions, and developing good exam habits."
- **Problem:** This step is about exam preparation, which is a different topic from the chapter 'A Question of Trust'.

### Grade 10 / English / Supplementary Reader - Chapter 5: Footprints without Feet — Exam preparation
- **Type:** TOPIC_MISMATCH
- **Quote:** "How can science make objects or people invisible?"
- **Problem:** This question is not related to the SOURCE_TEXT and is a topic mismatch.

### Grade 10 / English / Supplementary Reader - Chapter 5: Footprints without Feet — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "How can scientists determine whether the footprints are made by Griffin or someone else?"
- **Problem:** This question is not related to the SOURCE_TEXT and is a topic mismatch.

### Grade 10 / English / Supplementary Reader - Chapter 5: Footprints without Feet — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "What do you think would happen if Griffin’s experiment to become invisible was done without caution?"
- **Problem:** This question is not related to the SOURCE_TEXT and is a topic mismatch.

### Grade 10 / English / Supplementary Reader - Chapter 6: The Making of a Scientist — Exam preparation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Today, we will learn how to prepare effectively for exams based on the chapter 'The Making of a Scientist.'"
- **Problem:** This step is about exam preparation, not the making of a scientist.

### Grade 10 / English / Supplementary Reader - Chapter 6: The Making of a Scientist — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Today, we will learn how to approach and solve worked examples effectively."
- **Problem:** This step is about worked examples in science and mathematics, not the making of a scientist.

### Grade 10 / English / Supplementary Reader - Chapter 7: The Necklace — Core explanation
- **Type:** FABRICATED_NUMBER
- **Quote:** "Suppose Madame Loisel borrowed a necklace worth 36,000 francs but lost it."
- **Problem:** The original source text does not provide a specific value for the necklace, and the value of 36,000 francs appears to be fabricated.

### Grade 10 / English / Supplementary Reader - Chapter 7: The Necklace — Exam preparation
- **Type:** TOPIC_MISMATCH
- **Quote:** "# Lesson on Relative Clauses from the Chapter "The Necklace" (Grade 10, CBSE)"
- **Problem:** This step's content is about relative clauses, which is a different topic from the story "The Necklace".

### Grade 10 / English / Text Book - Chapter 1: A Letter to God — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "The chapter 'A Letter to God' is a story that revolves around a young girl named Sophie who writes a letter to God after her mother's death."
- **Problem:** The chapter actually revolves around a young boy, not a girl named Sophie.

### Grade 10 / English / Workbook - Chapter 7: Madam Rides the Bus — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "The given textbook context is from the chapter 'Madam Rides the Bus' and covers various aspects such as Valli's desire to ride the bus, her planning and execution, and the conversations she has with the conductor and other passengers."
- **Problem:** This step's content is about exam-style problems in general, not specifically about the chapter 'Madam Rides the Bus'. It seems to be a mismatched topic.

### Grade 10 / Hindi / अध्याय 10: मन्नू भंडारी — Exam preparation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Lesson on Exam Preparation for "अध्याय 10: मन्नू भंडारी" (Sub-topic: Exam Preparation)"
- **Problem:** यह पाठ अध्याय 10 के बारे में नहीं है, बल्कि परीक्षा तैयारी के बारे में है।

### Grade 10 / Hindi / अध्याय 10: मन्नू भंडारी — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "शीला अग्रवाल, साहित्य और वैचारिक विस्तार: अध्याय 10: मन्नू भंडारी"
- **Problem:** यह पाठ अध्याय 10 के बारे में नहीं है, बल्कि शीला अग्रवाल और साहित्य के बारे में है।

### Grade 10 / Hindi / अध्याय 11: यतींद्र मिश्र — Exam preparation ---
- **Type:** TOPIC_MISMATCH
- **Quote:** "Lesson on "अध्याय 11: यतींद्र मिश्र" - विशेष रूप से बिस्मिल्ला खाँ का व्यक्तित्व और संगीत साधना"
- **Problem:** यह पाठ अध्याय 11: यतींद्र मिश्र के बारे में है, लेकिन इसमें बिस्मिल्ला खाँ के बारे में विशेष रूप से चर्चा की जा रही है, जो अध्याय 11 के विषय से मेल नहीं खाता है।

### Grade 10 / Hindi / अध्याय 12: भदंत आनंद कौसल्यायन — Exam preparation
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will focus on how to prepare effectively for exams based on the chapter about भदंत आनंद कौसल्यायन."
- **Problem:** यह पाठ अध्याय 12: भदंत आनंद कौसल्यायन के बारे में है, लेकिन यहाँ का विषय परीक्षा तैयारी है, जो अध्याय 12 के साथ संबंधित नहीं है।

### Grade 10 / Hindi / अध्याय 12: भदंत आनंद कौसल्यायन — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "आप मानव संस्कृति की अविभाज्यता, प्रज्ञा और मैत्री के महत्त्व को समझेंगे।"
- **Problem:** यह पाठ अध्याय 12: भदंत आनंद कौसल्यायन के बारे में है, लेकिन यहाँ का विषय परीक्षा शैली के प्रश्न हैं, जो अध्याय 12 के साथ संबंधित नहीं है।

### Grade 10 / Hindi / अध्याय 1: सूरदास — Exam preparation
- **Type:** TOPIC_MISMATCH
- **Quote:** "इस चरण में आप चौथे पद के राजनीतिक व्यंग्य, कृष्ण के बदले हुए व्यवहार और राजधर्म की अवधारणा को समझेंगे।"
- **Problem:** यह चरण अध्याय 1: सूरदास के लिए है, लेकिन यह अध्याय के संदर्भ में नहीं है।

### Grade 10 / Hindi / अध्याय 1: सूरदास — परीक्षा-शैली विश्लेषण
- **Type:** TOPIC_MISMATCH
- **Quote:** "इस चरण में आप चौथे पद के राजनीतिक व्यंग्य, कृष्ण के बदले हुए व्यवहार और राजधर्म की अवधारणा को समझेंगे।"
- **Problem:** यह चरण अध्याय 1: सूरदास के लिए है, लेकिन यह अध्याय के संदर्भ में नहीं है।

### Grade 10 / Hindi / अध्याय 4: सूर्यकांत त्रिपाठी 'निराला' — Exam preparation
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, you will learn how to prepare effectively for exams based on the chapter "सूर्यकांत त्रिपाठी 'निराल'"
- **Problem:** This step is about exam preparation, which is not the main topic of the chapter.

### Grade 10 / Hindi / अध्याय 4: सूर्यकांत त्रिपाठी 'निराला' — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, you will learn how to prepare effectively for exams based on the chapter "सूर्यकांत त्रिपाठी 'निराल'"
- **Problem:** This step is about exam preparation, which is not the main topic of the chapter.

### Grade 10 / Hindi / अध्याय 5: नागार्जुन — Exam preparation
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, you will learn how to prepare effectively for exams based on the chapter about नागार्जुन."
- **Problem:** This step is about exam preparation, which is not the focus of the provided source text. The topic mismatch is significant, as it indicates that the step is not relevant to the chapter.

### Grade 10 / Hindi / अध्याय 5: नागार्जुन — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "‘फसल’ में प्रकृति और श्रम: अध्याय 5: नागार्जुन"
- **Problem:** This step is about exam-style problems, which is not the focus of the provided source text. The topic mismatch is significant, as it indicates that the step is not relevant to the chapter.

### Grade 10 / Hindi / अध्याय 6: मंगलेश डबराल — Exam preparation
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will learn about how to prepare effectively for exams, especially focusing on the strategies, tips, and mindset needed to perform well in your Hindi exams and other subjects."
- **Problem:** यह पाठ अध्याय 6: मंगलेश डबराल के बारे में नहीं है, बल्कि परीक्षा तैयारी के बारे में है।

### Grade 10 / Hindi / अध्याय 7: स्वयं प्रकाश — Exam Preparation for अध्याय 7: स्वयं प्रकाश
- **Type:** TOPIC_MISMATCH
- **Quote:** "Exam preparation isn't just about reading the chapters once; it's about understanding the concepts deeply, practicing questions, and managing your time during the exam."
- **Problem:** यह एक अलग अध्याय है जो परीक्षा तैयारी पर केंद्रित है, न कि स्वयं प्रकाश पर।

### Grade 10 / Hindi / अध्याय 8: रामवृक्ष बेनीपुरी — Exam Preparation for CBSE Class 10 Hindi: अध्याय 8 - रामवृक्ष बेनीपुरी
- **Type:** TOPIC_MISMATCH
- **Quote:** "Exam Preparation for CBSE Class 10 Hindi"
- **Problem:** यह अध्याय का शीर्षक है, लेकिन पाठ का विषय रामवृक्ष बेनीपुरी है।

### Grade 10 / Hindi / अध्याय 9: यशपाल — Exam preparation
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will focus on how to prepare effectively for exams based on the chapter about यशपाल."
- **Problem:** यह पाठ अध्याय 9: यशपाल के बारे में नहीं, बल्कि परीक्षा तैयारी के बारे में है।

### Grade 10 / Hindi / अध्याय 9: यशपाल — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "Question: You are preparing for an exam on the chapter about यशपाल. Write a short note on his contributions to Indian literature and social issues."
- **Problem:** यह प्रश्न अध्याय 9: यशपाल के बारे में नहीं, बल्कि परीक्षा में पूछे जाने वाले प्रश्नों के बारे में है।

### Grade 10 / Maths / Chapter 2: Polynomials — Exam preparation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will focus on exam preparation for polynomials, covering key concepts, important examples, and exam/reasoning points."
- **Problem:** This step is about exam preparation, which is not related to the chapter on polynomials.

### Grade 10 / Science / Chapter 10: The Human Eye and the Colourful World — Exam preparation
- **Type:** ARITHMETIC_ERROR
- **Quote:** "The focal length of the lens is calculated as f = 1/P, where P is the power of the lens in dioptres."
- **Problem:** The calculation f = 1/P is incorrect, as the correct formula is f = 1/P, where P is the power of the lens in dioptres, and the focal length is in meters. The correct calculation is f = 1/(2.5) = 0.4 meters, not -0.4 meters.

### Grade 10 / Science / Chapter 10: The Human Eye and the Colourful World — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will explain atmospheric refraction using changing air density and refractive index."
- **Problem:** This topic is not covered in the source text, and the explanation provided is not accurate.

### Grade 10 / Science / Chapter 11: Electricity — Exam preparation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Lesson on Electric Current and Its Regulation for Class 10 CBSE Science"
- **Problem:** This step's content is about a different chapter/topic than the given chapter label.

### Grade 10 / Science / Chapter 13: Our Environment — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "This chapter compares plastic cups, clay kulhads and paper cups, showing that alternatives must be judged by their total environmental impact."
- **Problem:** This statement seems to be discussing a different chapter or topic, as it is not related to the main topic of the chapter.

### Grade 10 / Science / Chapter 8: Heredity — Exam preparation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Sex-determination mechanisms differ among species."
- **Problem:** This statement is not relevant to the provided chapter label (Heredity) and appears to be a topic from a different chapter or subject.

### Grade 10 / Science / Chapter 8: Heredity — Exam-Style Problems: Heredity
- **Type:** TOPIC_MISMATCH
- **Quote:** "Sex-determination mechanisms differ among species."
- **Problem:** This statement is not relevant to the provided chapter label (Heredity) and appears to be a topic from a different chapter or subject.

### Grade 10 / Science / Chapter 8: Heredity — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Sex-determination mechanisms differ among species."
- **Problem:** This statement is not relevant to the provided chapter label (Heredity) and appears to be a topic from a different chapter or subject.

### Grade 10 / Science / Chapter 9: Light – Reflection and Refraction — Exam preparation
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will understand what happens when light passes from one transparent medium to another, focusing on the phenomenon called refraction."
- **Problem:** This step is about refraction, not reflection and refraction, which is the topic of the chapter.

### Grade 10 / Science / Chapter 9: Light – Reflection and Refraction — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will study convex and concave lenses, their ray diagrams and image rules."
- **Problem:** This step is about lenses, not reflection and refraction, which is the topic of the chapter.

### Grade 10 / Science / Chapter 9: Light – Reflection and Refraction — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "The safest way to solve an optics problem is to identify the device, predict the image qualitatively, assign signs, use the correct formula and then interpret the signs and magnitude of the answer."
- **Problem:** This step is about optics in general, not reflection and refraction, which is the topic of the chapter.

### Grade 10 / Social Science / Chapter 2: Nationalism in India — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will learn why the First World War created anger and hardship in India, how Gandhi defined satyagraha, and why the Rowlatt Act and Jallianwala Bagh widened anti-colonial protest."
- **Problem:** This step discusses the First World War and its impact on India, which is not the topic of Chapter 2: Nationalism in India.

### Grade 10 / Social Science / Chapter 2: Nationalism in India — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "The movement became national because many local struggles connected themselves to Gandhi and the Congress."
- **Problem:** This step discusses the Non-Cooperation Movement, which is not the main topic of Chapter 2: Nationalism in India. The chapter label suggests that the topic is Nationalism in India, but the content is about the Non-Cooperation Movement.

### Grade 10 / Social Science / Chapter 2: Nationalism in India — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will compare why peasants, business groups, workers and women participated in Civil Disobedience."
- **Problem:** This step discusses the Civil Disobedience Movement, which is not the main topic of Chapter 2: Nationalism in India. The chapter label suggests that the topic is Nationalism in India, but the content is about the Civil Disobedience Movement.

### Grade 10 / Social Science / Chapter 2: Nationalism in India — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will revise how cultural images, songs, folklore, flags and historical writing created a sense of collective belonging."
- **Problem:** This step discusses the cultural aspects of nationalism, which is not the main topic of Chapter 2: Nationalism in India. The chapter label suggests that the topic is Nationalism in India, but the content is about the cultural aspects of nationalism.

### Grade 10 / Social Science / Chapter 2: Nationalism in India — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will trace the shift from Non-Cooperation to the demand for Purna Swaraj and the Civil Disobedience Movement."
- **Problem:** This step discusses the Civil Disobedience Movement, which is not the main topic of Chapter 2: Nationalism in India. The chapter label suggests that the topic is Nationalism in India, but the content is about the Civil Disobedience Movement.

### Grade 10 / Social Science / Chapter 3: Gender, Religion and Caste — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will explain how the caste system produced social and economic inequality and why its effects continue despite constitutional prohibition."
- **Problem:** This step is supposed to be about gender, religion, and caste, but it is actually about the caste system, which is a different topic.

### Grade 10 / Social Science / Chapter 3: Gender, Religion and Caste — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will distinguish a legitimate relationship between religion and politics from communal politics."
- **Problem:** This step is supposed to be about gender, religion, and caste, but it is actually about communalism, which is a different topic.

### Grade 10 / Social Science / Chapter 4: The Age of Industrialisation — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Tracing the change from India’s strong pre-colonial textile trade to East India Company control and the arrival of Manchester goods."
- **Problem:** This step is about the decline of the Indian textile trade, which is a different topic from the rest of the chapter.

### Grade 10 / Social Science / Chapter 5: Minerals and Energy Resources — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will study conventional energy resources and their distribution. You will distinguish coal types, petroleum, natural gas, hydel power and thermal power."
- **Problem:** This step is about conventional energy resources, not minerals and energy resources as the chapter label suggests.

### Grade 10 / Social Science / Chapter 5: Minerals and Energy Resources — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will compare non-conventional energy sources and revise the need for energy conservation. You will evaluate why renewable energy is important for India’s future."
- **Problem:** This step is about non-conventional energy sources, not minerals and energy resources as the chapter label suggests.

### Grade 10 / Social Science / Chapter 5: Minerals and Energy Resources — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will analyse mining hazards and explain why mineral conservation is necessary. You will connect the slow formation of minerals with sustainable use."
- **Problem:** This step is about mining hazards and mineral conservation, not minerals and energy resources as the chapter label suggests.

### Grade 10 / Social Science / Chapter 5: Outcomes of Democracy — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will explain how democracy accommodates social diversity and state the conditions under which majority rule remains democratic."
- **Problem:** This step's content is about a different chapter/topic, 'accommodating social diversity', rather than the given chapter label, 'Outcomes of Democracy'.

### Grade 10 / Social Science / Chapter 6: Manufacturing Industries — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will classify the main forms of industrial pollution."
- **Problem:** This topic does not match the chapter label 'Manufacturing Industries'. The chapter does not cover industrial pollution.

### Grade 10 / Social Science / Chapter 6: Manufacturing Industries — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will revise methods for controlling industrial pollution."
- **Problem:** This topic does not match the chapter label 'Manufacturing Industries'. The chapter does not cover industrial pollution.

### Grade 10 / Social Science / Chapter 6: Manufacturing Industries — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will compare basic, metallurgical, chemical, construction, automobile and electronic industries."
- **Problem:** This topic does not match the chapter label 'Manufacturing Industries'. The chapter does not cover the comparison of these industries.

### Grade 10 / Social Science / Chapter 7: Lifelines of National Economy — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will distinguish local and international trade and understand balance of trade."
- **Problem:** This topic is not covered in the provided SOURCE_TEXT, which focuses on transport and communication systems.

### Grade 10 / Social Science / Geography - Chapter 3: Water Resources — Exam preparation
- **Type:** FABRICATED_NUMBER
- **Quote:** "Water covers three-fourths of the earth's surface"
- **Problem:** This statement is not supported by the source text and is likely a fabricated number.

### Grade 10 / Social Science / Geography - Chapter 3: Water Resources — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "Regions with high annual rainfall and large population"
- **Problem:** This step is about classifying situations related to water scarcity, but it does not match the topic of the chapter.

### Grade 10 / Social Science / Geography - Chapter 3: Water Resources — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Pipes passing over roads or land, they are placed high above to prevent damage and allow safe crossing."
- **Problem:** This step is about water management, but it does not match the topic of the chapter.

### Grade 10 / Social Science / Geography - Chapter 3: Water Resources — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Calculating water availability in a region"
- **Problem:** This step is about water management, but it does not match the topic of the chapter.

### Grade 10 / Social Science / History - Chapter 2: Nationalism in India — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will explore the concept of money—what it is, how it has evolved over time, and its role in our economy."
- **Problem:** This step is about the concept of money, which is a different topic from nationalism in India.

### Grade 11 / Accountancy / Chapter 1: Introduction to Accounting — Worked examples: Introduction to Accounting
- **Type:** ARITHMETIC_ERROR
- **Quote:** "The business earned a profit of ₹60,000."
- **Problem:** The calculation is incorrect, as the revenue is ₹6,00,000 and the expenses are ₹5,40,000, resulting in a profit of ₹1,60,000, not ₹60,000.

### Grade 11 / Accountancy / Chapter 4: Recording of Transactions – II — Concept Introduction: Recording of Transactions – II
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will understand why the journal is divided into subsidiary books. You will identify which repetitive transactions belong in each special-purpose book."
- **Problem:** This step is supposed to introduce the concept of recording transactions in subsidiary books, but it actually discusses the division of labour and the use of special-purpose books.

### Grade 11 / Accountancy / Chapter 4: Recording of Transactions – II — Revision and Recap: Recording of Transactions – II
- **Type:** TOPIC_MISMATCH
- **Quote:** "Journal proper is the residual journal. It records opening, closing, adjusting, transfer, rectification and other uncommon transactions after special books have captured routine items."
- **Problem:** This step is supposed to revise the complete subsidiary-book system, but it actually focuses on journal proper and its role in recording residual transactions.

### Grade 11 / Biology / Chapter 15: Body Fluids and Circulation — Worked Example on Enzyme Action in Biological Reactions
- **Type:** TOPIC_MISMATCH
- **Quote:** "The enzyme amylase helps break down starch into simpler sugars in our saliva."
- **Problem:** This topic is actually about enzyme action in biological reactions, which is not related to the chapter on body fluids and circulation.

### Grade 11 / Biology / Chapter 17: Locomotion and Movement — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "organise the axial and appendicular skeleton and classify joints from anatomical examples."
- **Problem:** This step appears to be about the skeletal system, which is a different topic from locomotion and movement.

### Grade 11 / Biology / Chapter 18: Neural Control and Coordination — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "The brain is a protected, regionally specialised CNS organ with forebrain, midbrain and hindbrain."
- **Problem:** This step appears to be discussing the brain, which is not the topic of the chapter on neural control and coordination.

### Grade 11 / Biology / Chapter 2: Biological Classification — Concept Introduction to Biological Classification
- **Type:** TOPIC_MISMATCH
- **Quote:** "Humans have tried to classify living things since ancient times."
- **Problem:** This step is about the history of classification, but the topic is supposed to be Chapter 2: Biological Classification, which is about the five-kingdom system.

### Grade 11 / Biology / Chapter 2: Biological Classification — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "Fungi are absorptive heterotrophs with chitin-containing walls."
- **Problem:** This step is about fungi, but the topic is supposed to be Chapter 2: Biological Classification, which is about the five-kingdom system.

### Grade 11 / Biology / Chapter 2: Biological Classification — Exam-style problems: Chapter 2: Biological Classification
- **Type:** TOPIC_MISMATCH
- **Quote:** "In ancient times, humans classified organisms based on their utility—food, shelter, clothing—without scientific criteria."
- **Problem:** This step is about the history of classification, but the topic is supposed to be Chapter 2: Biological Classification, which is about the five-kingdom system.

### Grade 11 / Biology / Chapter 2: Biological Classification — Lesson on Worked Examples in Biological Classification
- **Type:** TOPIC_MISMATCH
- **Quote:** "In biological classification, scientists group organisms based on shared features."
- **Problem:** This step is about the process of classification, but the topic is supposed to be Chapter 2: Biological Classification, which is about the five-kingdom system.

### Grade 11 / Biology / Chapter 2: Biological Classification — Revision and recap: Chapter 2: Biological Classification
- **Type:** TOPIC_MISMATCH
- **Quote:** "Some biological entities do not fit neatly into cellular kingdoms."
- **Problem:** This step is about the limitations of earlier classification systems, but the topic is supposed to be Chapter 2: Biological Classification, which is about the five-kingdom system.

### Grade 11 / Biology / Chapter 5: Morphology of Flowering Plants — Core explanation: Chapter 5: Morphology of Flowering Plants
- **Type:** TOPIC_MISMATCH
- **Quote:** "Core explanation: Chapter 5: Morphology of Flowering Plants"
- **Problem:** This step's content is a duplicate of the chapter title and does not provide any actual explanation or content related to the topic.

### Grade 11 / Biology / Chapter 5: Morphology of Flowering Plants — Exam-style problems: Chapter 5: Morphology of Flowering Plants
- **Type:** TOPIC_MISMATCH
- **Quote:** "Exam-style problems: Chapter 5: Morphology of Flowering Plants"
- **Problem:** This step's content is a duplicate of the chapter title and does not provide any actual explanation or content related to the topic.

### Grade 11 / Biology / Chapter 5: Morphology of Flowering Plants — Revision and recap: Chapter 5: Morphology of Flowering Plants
- **Type:** TOPIC_MISMATCH
- **Quote:** "Revision and recap: Chapter 5: Morphology of Flowering Plants"
- **Problem:** This step's content is a duplicate of the chapter title and does not provide any actual explanation or content related to the topic.

### Grade 11 / Biology / Chapter 5: Morphology of Flowering Plants — Worked examples: Chapter 5: Morphology of Flowering Plants
- **Type:** TOPIC_MISMATCH
- **Quote:** "Worked examples: Chapter 5: Morphology of Flowering Plants"
- **Problem:** This step's content is a duplicate of the chapter title and does not provide any actual explanation or content related to the topic.

### Grade 11 / Biology / Chapter 6: Anatomy of Flowering Plants — Exam-style problems --- # Exam-style problems: Chapter 6: Anatomy of Flowering Plants
- **Type:** TOPIC_MISMATCH
- **Quote:** "The arrangement of petals or sepals in a flower bud helps in flower identification and classification."
- **Problem:** This step is about aestivation, which is a topic from Chapter 5, not Chapter 6.

### Grade 11 / Biology / Chapter 6: Anatomy of Flowering Plants — Worked examples --- # Worked Example: Photosynthesis and Limiting Factors
- **Type:** TOPIC_MISMATCH
- **Quote:** "Photosynthesis rate depends on various environmental factors."
- **Problem:** This step is about photosynthesis, which is a topic from Chapter 7, not Chapter 6.

### Grade 11 / Biology / Chapter 7: Structural Organisation in Animals — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "A cell is like a tiny building block that makes up all living things, from tiny bacteria to huge elephants."
- **Problem:** This step is about the cell theory, but the chapter label is about structural organisation in animals.

### Grade 11 / Biology / Chapter 7: Structural Organisation in Animals — Worked Example on Photosynthesis in Higher Plants
- **Type:** TOPIC_MISMATCH
- **Quote:** "The graph below shows the rate of photosynthesis of a plant at different light intensities."
- **Problem:** This step is about photosynthesis, but the chapter label is about structural organisation in animals.

### Grade 11 / Biology / Chapter 8: Cell: The Unit of Life — Core Explanation of the Cell: The Unit of Life
- **Type:** TOPIC_MISMATCH
- **Quote:** "The cell's structure is designed to help it perform its functions efficiently."
- **Problem:** This step is discussing the general concept of cell structure and function, but it does not match the specific topic of the chapter, which is focused on the cell as the unit of life.

### Grade 11 / Biology / Chapter 8: Cell: The Unit of Life — Exam-style problems: Chapter 8: Cell: The Unit of Life
- **Type:** TOPIC_MISMATCH
- **Quote:** "The question requires you to explain the graph, which indicates that as salt concentration increases, the rate of osmosis decreases."
- **Problem:** This step is discussing a specific question and its solution, but it does not match the specific topic of the chapter, which is focused on the cell as the unit of life.

### Grade 11 / Biology / Chapter 8: Cell: The Unit of Life — Revision and recap: Chapter 8: Cell: The Unit of Life
- **Type:** TOPIC_MISMATCH
- **Quote:** "The nucleus is a membrane-bound organelle with a double membrane called the nuclear envelope."
- **Problem:** This step is discussing the general concept of the nucleus, but it does not match the specific topic of the chapter, which is focused on the cell as the unit of life.

### Grade 11 / Biology / Chapter 8: Cell: The Unit of Life — Worked examples: Chapter 8: Cell: The Unit of Life
- **Type:** TOPIC_MISMATCH
- **Quote:** "The plasma membrane is a dynamic lipid–protein mosaic that controls exchange, while the plant cell wall provides external support and communication pathways."
- **Problem:** This step is discussing the general concept of plasma membrane and plant cell wall, but it does not match the specific topic of the chapter, which is focused on the cell as the unit of life.

### Grade 11 / Biology / Digestion and Absorption — Lesson on Exam-Style Problems in Digestion and Absorption (Grade 11 Biology)
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will learn how to approach and solve exam-style problems related to digestion and absorption."
- **Problem:** This lesson step is about exam-style problems, but the chapter label is about digestion and absorption in Grade 11 Biology.

### Grade 11 / Biology / Digestion and Absorption — Revision and recap of Digestion and Absorption
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will review the key concepts of digestion and absorption, focusing on understanding the processes, their significance, and how different factors influence them."
- **Problem:** This lesson step is about digestion and absorption, but the chapter label is about digestion and absorption in Grade 11 Biology.

### Grade 11 / Biology / Digestion and Absorption — Worked Example: Understanding the Effect of Light Intensity on Photosynthesis
- **Type:** TOPIC_MISMATCH
- **Quote:** "The following data shows the rate of photosynthesis (measured as oxygen production in units per hour) at different light intensities (measured in lux)."
- **Problem:** This lesson step is about photosynthesis, but the chapter label is about digestion and absorption in Grade 11 Biology.

### Grade 11 / Business Studies / Chapter 1: Business, Trade and Commerce — Concept Introduction: Business, Trade and Commerce
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will understand why business is central to production, distribution and consumption."
- **Problem:** The chapter label is Chapter 1: Business, Trade and Commerce, but the content discusses the role of business in production, distribution, and consumption, which is more relevant to a later chapter.

### Grade 11 / Business Studies / Chapter 1: Business, Trade and Commerce — Core Explanation: Business, Trade and Commerce
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will learn the exact meaning and characteristics of business."
- **Problem:** The chapter label is Chapter 1: Business, Trade and Commerce, but the content focuses on the definition and characteristics of business, which is more relevant to a later chapter.

### Grade 11 / Business Studies / Chapter 1: Business, Trade and Commerce — Exam-style problems: Business, Trade and Commerce
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will understand trade and the auxiliaries that remove obstacles in exchange."
- **Problem:** The chapter label is Chapter 1: Business, Trade and Commerce, but the content discusses trade and auxiliaries, which is more relevant to a later chapter.

### Grade 11 / Business Studies / Chapter 1: Business, Trade and Commerce — Revision and recap: Business, Trade and Commerce
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will revise the nature and causes of business risk and the decisions required before launching an enterprise."
- **Problem:** The chapter label is Chapter 1: Business, Trade and Commerce, but the content focuses on business risk and entrepreneurship, which is more relevant to a later chapter.

### Grade 11 / Business Studies / Chapter 1: Business, Trade and Commerce — Worked Examples: Business, Trade and Commerce
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will classify industry and understand how commerce supports exchange."
- **Problem:** The chapter label is Chapter 1: Business, Trade and Commerce, but the content discusses industry and commerce, which is more relevant to a later chapter.

### Grade 11 / Business Studies / Chapter 4: Business Services — Revision and Recap: Business Services
- **Type:** TOPIC_MISMATCH
- **Quote:** "Businesses need fast links with suppliers and customers, physical movement of goods and scientific storage."
- **Problem:** This step's content is about communication, transportation, and warehousing services, which is a different chapter/topic than the given chapter label.

### Grade 11 / Business Studies / Chapter 6: Social Responsibilities of Business and Business Ethics — Revision and Recap: Social Responsibilities of Business and Business Ethics
- **Type:** TOPIC_MISMATCH
- **Quote:** "Key terms: legal responsibility, voluntary action, Corporate Social Responsibility, long-term interest, government regulation, labour movement, economic responsibility, legal responsibility, ethical responsibility, air pollution, water pollution, land pollution, top management commitment, employee involvement."
- **Problem:** This step is discussing various terms related to social responsibility, but it is not focused on the topic of environmental protection, which is mentioned in the source text.

### Grade 11 / Chemistry / Chapter 1: Some Basic Concepts of Chemistry — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Connect laws of chemical combination with Dalton atomic theory."
- **Problem:** This step is about Dalton's atomic theory, which is not the main topic of the chapter.

### Grade 11 / Chemistry / Chapter 4: Chemical Bonding and Molecular Structure — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Predict molecular shape using VSEPR theory."
- **Problem:** This step is about VSEPR theory, but the chapter label is about Chemical Bonding and Molecular Structure, which includes other topics like Lewis structures and molecular orbitals.

### Grade 11 / Chemistry / Chapter 5: Thermodynamics — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "Thermodynamics begins by choosing a system and specifying its condition."
- **Problem:** The chapter is actually about Equilibrium, not Thermodynamics.

### Grade 11 / Chemistry / Chapter 6: Equilibrium — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "Compare acid–base theories and calculate pH."
- **Problem:** This step is about acid-base theories, which is a different topic than Chapter 6: Equilibrium.

### Grade 11 / Chemistry / Chapter 6: Equilibrium — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Apply buffer, common-ion, hydrolysis, and solubility-product ideas."
- **Problem:** This step is about buffer, common-ion, hydrolysis, and solubility-product ideas, which is a different topic than Chapter 6: Equilibrium.

### Grade 11 / Chemistry / Chapter 6: Equilibrium — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Use Le Chatelier principle to predict shifts."
- **Problem:** This step is about Le Chatelier principle, which is a different topic than Chapter 6: Equilibrium.

### Grade 11 / Chemistry / Chapter 7: Redox Reactions — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Classify common redox reaction patterns."
- **Problem:** The topic of this step is about classifying redox reaction patterns, which is not related to the chapter label of Redox Reactions.

### Grade 11 / Chemistry / Chapter 8: Organic Chemistry – Some Basic Principles and Techniques — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "Use electronic effects to compare stability and classify reactions."
- **Problem:** This step is about electronic effects, which is not related to the topic of thermodynamics in the source text.

### Grade 11 / Chemistry / Chapter 8: Organic Chemistry – Some Basic Principles and Techniques — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Distinguish isomerism, bond fission, and reaction intermediates."
- **Problem:** This step is about isomerism, bond fission, and reaction intermediates, which is not related to the topic of thermodynamics in the source text.

### Grade 11 / Chemistry / Hydrogen — Exam-style problems
- **Type:** ARITHMETIC_ERROR
- **Quote:** "2.0156 + 15.995 = **18.0106 amu**"
- **Problem:** The calculation is mathematically wrong given its own stated inputs.

### Grade 11 / Economics / Chapter 10: Collection of Data — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will compare random and non-random sampling and understand sampling and non-sampling errors."
- **Problem:** This topic is not covered in the source text, which focuses on data collection methods and sources.

### Grade 11 / Economics / Chapter 10: Collection of Data — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will compare personal, mailed and telephone interviews and understand the purpose of a pilot survey."
- **Problem:** This topic is not covered in the source text, which focuses on data collection methods and sources.

### Grade 11 / Economics / Chapter 12: Presentation of Data — Revision and recap: Presentation of Data
- **Type:** TOPIC_MISMATCH
- **Quote:** "A suitable presentation is meaningful, comprehensive, and purposeful."
- **Problem:** This step is about choosing the right form of presentation, but the source text is about the three forms of presentation: textual, tabular, and diagrammatic.

### Grade 11 / Economics / Chapter 12: Presentation of Data — Worked examples: Presentation of Data
- **Type:** TOPIC_MISMATCH
- **Quote:** "Geometric diagrams turn categories and components into lengths or areas."
- **Problem:** This step is about choosing diagrams according to the comparison required, but the source text is about the three forms of presentation: textual, tabular, and diagrammatic.

### Grade 11 / Economics / Chapter 14: Correlation — Core explanation: Correlation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Index Numbers Studying this chapter should enable you to: understand the meaning of the term index number; become familiar with the use of some widely used index numbers; calculate an index number; appreciate its limitations."
- **Problem:** The topic of this chapter is Index Numbers, not Correlation.

### Grade 11 / Economics / Chapter 14: Correlation — Exam-style problems: Correlation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Index Numbers Studying this chapter should enable you to: understand the meaning of the term index number; become familiar with the use of some widely used index numbers; calculate an index number; appreciate its limitations."
- **Problem:** The topic of this chapter is Index Numbers, not Correlation.

### Grade 11 / Economics / Chapter 14: Correlation — Revision and recap: Correlation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Index Numbers Studying this chapter should enable you to: understand the meaning of the term index number; become familiar with the use of some widely used index numbers; calculate an index number; appreciate its limitations."
- **Problem:** The topic of this chapter is Index Numbers, not Correlation.

### Grade 11 / Economics / Chapter 14: Correlation — Worked examples: Correlation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Index Numbers Studying this chapter should enable you to: understand the meaning of the term index number; become familiar with the use of some widely used index numbers; calculate an index number; appreciate its limitations."
- **Problem:** The topic of this chapter is Index Numbers, not Correlation.

### Grade 11 / Economics / Chapter 2: Indian Economy 1950–1990 — Revision and recap: Indian Economy 1950–1990
- **Type:** TOPIC_MISMATCH
- **Quote:** "Transition: These limitations formed part of the background to later reform, though the 1991 reforms belong to the next chapter."
- **Problem:** This step discusses the 1991 reforms, which are not part of the current chapter.

### Grade 11 / Economics / Chapter 4: Human Capital Formation in India — Exam-style problems: Human Capital Formation in India
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will study the government’s role in human capital formation and the institutions involved."
- **Problem:** This step is about the government's role in human capital formation, which is a different topic from rural development, the main topic of the chapter.

### Grade 11 / Economics / Chapter 4: Human Capital Formation in India — Revision and recap: Human Capital Formation in India
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will evaluate India’s progress and continuing challenges in education and human capital."
- **Problem:** This step is about India's progress and challenges in education and human capital, which is a different topic from rural development, the main topic of the chapter.

### Grade 11 / Economics / Chapter 4: Human Capital Formation in India — Worked examples: Human Capital Formation in India
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will distinguish human capital from human development."
- **Problem:** This step is about distinguishing human capital from human development, which is a different topic from rural development, the main topic of the chapter.

### Grade 11 / Economics / Chapter 6: Employment: Growth, Informalisation and Other Issues — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Government employment programmes such as MNREGA, now referred to in the text as Viksit Bharat–Guarantee for Rozgar and Ajeevika Mission (Gramin), seek rural employment and income support."
- **Problem:** This topic is not discussed in the source text, which focuses on employment and environmental issues.

### Grade 11 / Geography / Chapter 18: Climate — Concept introduction --- # Concept introduction: Climate
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will distinguish weather from climate and understand monsoon unity with regional variation."
- **Problem:** This step is about the concept of climate, but the chapter label is 'Climate', which is correct, however, the topic mismatch is due to the fact that the chapter is actually about continental drift and not climate.

### Grade 11 / Geography / Chapter 18: Climate — Core explanation --- # Core explanation: Climate
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will study the main geographical controls of India’s climate."
- **Problem:** This step is about the geographical controls of climate, but the chapter label is 'Climate', which is correct, however, the topic mismatch is due to the fact that the chapter is actually about continental drift and not climate.

### Grade 11 / Geography / Chapter 18: Climate — Exam-style problems --- # Exam-style problems: Climate
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will follow the cold, hot, southwest monsoon and retreating monsoon seasons."
- **Problem:** This step is about the exam-style problems related to climate, but the chapter label is 'Climate', which is correct, however, the topic mismatch is due to the fact that the chapter is actually about continental drift and not climate.

### Grade 11 / Geography / Chapter 18: Climate — Revision and recap --- # Revision and recap: Climate
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will review rainfall regions, monsoon economics and global warming."
- **Problem:** This step is about the revision and recap of climate, but the chapter label is 'Climate', which is correct, however, the topic mismatch is due to the fact that the chapter is actually about continental drift and not climate.

### Grade 11 / Geography / Chapter 18: Climate — Worked examples --- # Worked examples: Climate
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will understand the ITCZ, cross-equatorial winds, jet streams, onset and breaks."
- **Problem:** This step is about the worked examples related to climate, but the chapter label is 'Climate', which is correct, however, the topic mismatch is due to the fact that the chapter is actually about continental drift and not climate.

### Grade 11 / Geography / Chapter 20: Natural Hazards and Disasters — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "A hazard has potential to harm, while a disaster is severe realised disruption."
- **Problem:** This step discusses the concepts of hazard and disaster, which are not related to the chapter's content about geomorphic processes and natural hazards.

### Grade 11 / Geography / Chapter 20: Natural Hazards and Disasters — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Tectonic earthquakes release accumulated energy, while weak construction and dense settlement increase damage."
- **Problem:** This step discusses earthquakes, which is not the main topic of the chapter about geomorphic processes and natural hazards.

### Grade 11 / Geography / Chapter 20: Natural Hazards and Disasters — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "Floods result from excess water, while droughts reflect prolonged shortage. Monsoon variability and land use influence both."
- **Problem:** This step discusses floods and droughts, which is not the main topic of the chapter about geomorphic processes and natural hazards.

### Grade 11 / Geography / Chapter 20: Natural Hazards and Disasters — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Landslide vulnerability and the stages of disaster management are studied."
- **Problem:** This step discusses landslide vulnerability and disaster management, which is not the main topic of the chapter about geomorphic processes and natural hazards.

### Grade 11 / Geography / Chapter 20: Natural Hazards and Disasters — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Tsunamis begin with sudden sea-floor displacement; cyclones draw energy from warm moist oceanic air."
- **Problem:** This step discusses tsunamis and cyclones, which is not the main topic of the chapter about geomorphic processes and natural hazards.

### Grade 11 / Geography / Chapter 2: The Origin and Evolution of the Earth — Concept introduction
- **Type:** UNSUPPORTED_CLAIM
- **Quote:** "Scientific origin ideas changed as observations broadened from the solar system to the universe."
- **Problem:** This statement is not supported by the SOURCE_TEXT, which focuses on the origin and evolution of the Earth, not the universe.

### Grade 11 / Geography / Chapter 2: The Origin and Evolution of the Earth — Concept introduction
- **Type:** UNSUPPORTED_CLAIM
- **Quote:** "The Nebular Hypothesis and Big Bang Theory explain different stages."
- **Problem:** This statement is not supported by the SOURCE_TEXT, which does not mention the Big Bang Theory or its relation to the Nebular Hypothesis.

### Grade 11 / Geography / Chapter 2: The Origin and Evolution of the Earth — Core explanation
- **Type:** UNSUPPORTED_CLAIM
- **Quote:** "Expansion and cooling changed the early universe, while uneven matter and gravity formed galaxies and stars."
- **Problem:** This statement is not supported by the SOURCE_TEXT, which focuses on the origin and evolution of the Earth, not the universe.

### Grade 11 / Geography / Chapter 2: The Origin and Evolution of the Earth — Exam-style problems
- **Type:** UNSUPPORTED_CLAIM
- **Quote:** "Cooling and density separation produced internal layers, while gases and water vapour from the interior formed a later atmosphere and hydrosphere."
- **Problem:** This statement is not supported by the SOURCE_TEXT, which focuses on the origin and evolution of the Earth, not the early Earth's atmosphere and hydrosphere.

### Grade 11 / Geography / Chapter 2: The Origin and Evolution of the Earth — Revision and recap
- **Type:** UNSUPPORTED_CLAIM
- **Quote:** "Chemical processes produced complex organic molecules, early life appeared in oceans and later modified the atmosphere."
- **Problem:** This statement is not supported by the SOURCE_TEXT, which does not discuss the chemical origin of life or its modification of the atmosphere.

### Grade 11 / Geography / Chapter 2: The Origin and Evolution of the Earth — Worked examples
- **Type:** UNSUPPORTED_CLAIM
- **Quote:** "Gas and dust around a young star condensed into small bodies that collided and grew into planets."
- **Problem:** This statement is not supported by the SOURCE_TEXT, which focuses on the origin and evolution of the Earth, not the formation of planets.

### Grade 11 / Geography / Chapter 3: Interior of the Earth — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "Direct samples come from shallow rocks and volcanic material, while deep structure is inferred from heat, pressure, gravity, magnetism and seismic waves."
- **Problem:** This step discusses the limitations of directly observing the Earth's interior, but the chapter label is 'Interior of the Earth', which suggests a focus on the internal structure of the Earth, not just the limitations of observation.

### Grade 11 / Geography / Chapter 3: Interior of the Earth — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will compare volcanic types and intrusive igneous forms."
- **Problem:** This step discusses volcanic types and intrusive igneous forms, but the chapter label is 'Interior of the Earth', which suggests a focus on the internal structure of the Earth, not just the types of volcanoes and igneous rocks.

### Grade 11 / Geography / Chapter 4: Distribution of Oceans and Continents — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "Continents and oceans have changed position. Wegener proposed one former supercontinent surrounded by a mega-ocean."
- **Problem:** This step is about continental drift theory and the breakup of Pangaea, but the chapter label is about the distribution of oceans and continents.

### Grade 11 / Geography / Chapter 4: Distribution of Oceans and Continents — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Similar rocks, glacial deposits, minerals and fossils across separated continents support earlier connection."
- **Problem:** This step is about evidence for drift and Wegener's proposed forces, but the chapter label is about the distribution of oceans and continents.

### Grade 11 / Geography / Chapter 4: Distribution of Oceans and Continents — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will understand plate tectonics and the three boundary types."
- **Problem:** This step is about plate tectonics and boundary types, but the chapter label is about the distribution of oceans and continents.

### Grade 11 / Geography / Chapter 4: Distribution of Oceans and Continents — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will study mantle convection and the movement of the Indian Plate."
- **Problem:** This step is about mantle convection and the Indian Plate, but the chapter label is about the distribution of oceans and continents.

### Grade 11 / Geography / Chapter 4: Distribution of Oceans and Continents — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will study ocean-floor discoveries and Hess’s sea-floor spreading hypothesis."
- **Problem:** This step is about ocean-floor discoveries and sea-floor spreading, but the chapter label is about the distribution of oceans and continents.

### Grade 11 / Geography / Chapter 9: Atmospheric Circulation and Weather Systems — Worked examples: Atmospheric Circulation and Weather Systems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will follow general circulation from the ITCZ through Hadley, Ferrel and polar cells."
- **Problem:** This step appears to be discussing the general circulation of the atmosphere, which is a topic that is typically covered in a separate chapter or section. The previous steps in this chapter have been discussing atmospheric circulation and weather systems, but this step seems to be straying into a different topic area.

### Grade 11 / Hindi / Chapter 8: Bharat Mata — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "किसानों की तकलीफ़ें एक-सी थी"
- **Problem:** यह प्रसंग किसानों की साझी समस्याओं को स्पष्ट करता है, जो चैप्टर के विषय से मेल नहीं खाता है।

### Grade 11 / Hindi / Chapter 8: Bharat Mata — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "भारत माता धरती से भी अधिक व्यापक है"
- **Problem:** यह प्रसंग भारत माता की अवधारणा को स्पष्ट करता है, जो चैप्टर के विषय से मेल नहीं खाता है।

### Grade 11 / Hindi / Chapter 8: Bharat Mata — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "भारत माता वास्तव में करोड़ों लोग हैं"
- **Problem:** यह प्रसंग जन-केंद्रित राष्ट्रबोध को स्पष्ट करता है, जो चैप्टर के विषय से मेल नहीं खाता है।

### Grade 11 / Hindi / Chapter 8: Bharat Mata — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "महाकाव्यों और यात्राओं से देश का परिचय"
- **Problem:** यह प्रसंग विश्व-दृष्टि को स्पष्ट करता है, जो चैप्टर के विषय से मेल नहीं खाता है।

### Grade 11 / Hindi / Husain Ki Kahani Apni Zubani — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Husain was a famous artist known for his paintings and storytelling."
- **Problem:** This step's content is about a different chapter/topic, specifically about Husain as an artist, not Husain Ki Kahani Apni Zubani.

### Grade 11 / Hindi / Namak — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will understand what "Namak" (salt) is, its basic properties, and why it is important in our daily life."
- **Problem:** The topic of the lesson does not match the chapter label "Namak" which is about a short story called "Namak ka Daroga" by Premchand.

### Grade 11 / History / Chapter 1: Writing and City Life — Concept Introduction: Writing and City Life
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will locate Mesopotamia and understand how historians reconstruct its past."
- **Problem:** The chapter is about understanding oneself and the significance of developing a positive sense of self, but the lesson step is about Mesopotamia and city life.

### Grade 11 / History / Chapter 1: Writing and City Life — Core Explanation: Writing and City Life
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will understand the economic meaning of urbanism."
- **Problem:** The chapter is about understanding oneself and the significance of developing a positive sense of self, but the lesson step is about the economic meaning of urbanism.

### Grade 11 / History / Chapter 1: Writing and City Life — Exam-style Problems: Writing and City Life
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will explain how temples and kings shaped southern Mesopotamian cities."
- **Problem:** The chapter is about understanding oneself and the significance of developing a positive sense of self, but the lesson step is about temples and kings shaping southern Mesopotamian cities.

### Grade 11 / History / Chapter 1: Writing and City Life — Revision and Recap: Writing and City Life
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will connect Mesopotamian city culture with literature, mathematics, astronomy and preservation of knowledge."
- **Problem:** The chapter is about understanding oneself and the significance of developing a positive sense of self, but the lesson step is about connecting Mesopotamian city culture with literature, mathematics, astronomy and preservation of knowledge.

### Grade 11 / History / Chapter 1: Writing and City Life — Worked Examples: Writing and City Life
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will trace the emergence of writing and understand how cuneiform worked."
- **Problem:** The chapter is about understanding oneself and the significance of developing a positive sense of self, but the lesson step is about tracing the emergence of writing and understanding how cuneiform worked.

### Grade 11 / History / Chapter 2: An Empire Across Three Continents — Concept Introduction: An Empire Across Three Continents
- **Type:** TOPIC_MISMATCH
- **Quote:** "Rome controlled the Mediterranean and territories across Europe, North Africa and western Asia."
- **Problem:** This step is about the Roman Empire, but the chapter label is Grade 11 / History / Chapter 2: An Empire Across Three Continents, which is not about the Roman Empire.

### Grade 11 / History / Chapter 2: An Empire Across Three Continents — Core Explanation: An Empire Across Three Continents
- **Type:** TOPIC_MISMATCH
- **Quote:** "Augustus established one-man rule while preserving the appearance that the Senate still mattered."
- **Problem:** This step is about the Roman Empire, but the chapter label is Grade 11 / History / Chapter 2: An Empire Across Three Continents, which is not about the Roman Empire.

### Grade 11 / History / Chapter 2: An Empire Across Three Continents — Exam-style problems: An Empire Across Three Continents
- **Type:** TOPIC_MISMATCH
- **Quote:** "Rome’s economy linked fertile provinces, ports, mines, farms, workshops, banks and markets."
- **Problem:** This step is about the Roman economy, but the chapter label is Grade 11 / History / Chapter 2: An Empire Across Three Continents, which is not about the Roman economy.

### Grade 11 / History / Chapter 2: An Empire Across Three Continents — Revision and recap: An Empire Across Three Continents
- **Type:** TOPIC_MISMATCH
- **Quote:** "Late antiquity was not simply an age of decline."
- **Problem:** This step is about late antiquity, but the chapter label is Grade 11 / History / Chapter 2: An Empire Across Three Continents, which is not about late antiquity.

### Grade 11 / History / Chapter 2: An Empire Across Three Continents — Worked examples: An Empire Across Three Continents
- **Type:** TOPIC_MISMATCH
- **Quote:** "External invasion and internal conflict placed the empire under severe pressure in the third century."
- **Problem:** This step is about the Roman Empire, but the chapter label is Grade 11 / History / Chapter 2: An Empire Across Three Continents, which is not about the Roman Empire.

### Grade 11 / History / Chapter 4: The Three Orders — Concept Introduction: The Three Orders
- **Type:** TOPIC_MISMATCH
- **Quote:** "After Roman political unity collapsed, land control, military protection and Christianity shaped western European society."
- **Problem:** This step is discussing the collapse of Roman political unity and the shaping of Western European society, which is not related to the chapter label 'The Three Orders' in the context of medieval Europe.

### Grade 11 / History / Chapter 4: The Three Orders — Core Explanation: The Three Orders
- **Type:** TOPIC_MISMATCH
- **Quote:** "Nobles controlled land and exercised authority through reciprocal vows."
- **Problem:** This step is discussing nobles, vassalage, manors, and knights, which is not related to the chapter label 'The Three Orders' in the context of medieval Europe.

### Grade 11 / History / Chapter 4: The Three Orders — Exam-style problems: The Three Orders
- **Type:** TOPIC_MISMATCH
- **Quote:** "Feudal relationships were reshaped when warmer conditions and new technology increased production."
- **Problem:** This step is discussing the impact of climate, tools, crop rotation, and money on rural society, which is not related to the chapter label 'The Three Orders' in the context of medieval Europe.

### Grade 11 / History / Chapter 4: The Three Orders — Revision and recap: The Three Orders
- **Type:** TOPIC_MISMATCH
- **Quote:** "The fourteenth-century crisis, peasant resistance, and the rise of stronger monarchies."
- **Problem:** This step is discussing the fourteenth-century crisis, peasant resistance, and the rise of stronger monarchies, which is not related to the chapter label 'The Three Orders' in the context of medieval Europe.

### Grade 11 / History / Chapter 4: The Three Orders — Worked Examples: The Three Orders
- **Type:** TOPIC_MISMATCH
- **Quote:** "The power of the Church and the different lives of priests, monks, nuns, and friars."
- **Problem:** This step is discussing the power of the Church and the different lives of priests, monks, nuns, and friars, which is not related to the chapter label 'The Three Orders' in the context of medieval Europe.

### Grade 11 / History / Chapter 5: Changing Cultural Traditions — Concept Introduction: Changing Cultural Traditions
- **Type:** TOPIC_MISMATCH
- **Quote:** "From the fourteenth to the seventeenth century, Florence, Venice and Rome attracted artists, scholars and patrons."
- **Problem:** This step is about the Renaissance in Italy, but the chapter label is 'Changing Cultural Traditions' which is a broader topic.

### Grade 11 / History / Chapter 5: Changing Cultural Traditions — Core Explanation: Changing Cultural Traditions
- **Type:** TOPIC_MISMATCH
- **Quote:** "Humanists closely read ancient texts and taught grammar, rhetoric, poetry, history and moral philosophy."
- **Problem:** This step is about humanism and the Renaissance, but the chapter label is 'Changing Cultural Traditions' which is a broader topic.

### Grade 11 / History / Chapter 5: Changing Cultural Traditions — Exam-style Problems: Changing Cultural Traditions
- **Type:** TOPIC_MISMATCH
- **Quote:** "Humanists argued that people could shape their lives, pursue knowledge and develop many talents."
- **Problem:** This step is about humanism and the Renaissance, but the chapter label is 'Changing Cultural Traditions' which is a broader topic.

### Grade 11 / History / Chapter 5: Changing Cultural Traditions — Revision and Recap: Changing Cultural Traditions
- **Type:** TOPIC_MISMATCH
- **Quote:** "Printing and humanist reading encouraged Christians to challenge church practices, while scientists questioned an earth-centred universe."
- **Problem:** This step is about the Renaissance and the Scientific Revolution, but the chapter label is 'Changing Cultural Traditions' which is a broader topic.

### Grade 11 / History / Chapter 5: Changing Cultural Traditions — Worked Examples: Changing Cultural Traditions
- **Type:** TOPIC_MISMATCH
- **Quote:** "Humanist ideas travelled not only through classrooms but through images, buildings and books."
- **Problem:** This step is about the Renaissance and the impact of humanism on art and architecture, but the chapter label is 'Changing Cultural Traditions' which is a broader topic.

### Grade 11 / History / Chapter 6: Displacing Indigenous Peoples — Concept Introduction: Displacing Indigenous Peoples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will understand settler colonialism and why indigenous histories were long excluded from national narratives."
- **Problem:** This step is about settler colonialism, but the chapter label is 'Displacing Indigenous Peoples', which suggests a focus on the indigenous perspective.

### Grade 11 / History / Chapter 6: Displacing Indigenous Peoples — Core Explanation: Displacing Indigenous Peoples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will study North American native societies before and during early European contact."
- **Problem:** This step is about North American native societies, but the chapter label is 'Displacing Indigenous Peoples', which suggests a focus on the indigenous perspective in multiple regions.

### Grade 11 / History / Chapter 6: Displacing Indigenous Peoples — Exam-style Problems: Displacing Indigenous Peoples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will examine the contradiction between settler democracy and indigenous exclusion."
- **Problem:** This step is about settler democracy and indigenous exclusion in the United States and Canada, but the chapter label is 'Displacing Indigenous Peoples', which suggests a focus on the indigenous perspective in multiple regions.

### Grade 11 / History / Chapter 6: Displacing Indigenous Peoples — Revision and Recap: Displacing Indigenous Peoples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will compare Australian settler history with North America and trace the shift from terra nullius to recognition, multiculturalism and apology."
- **Problem:** This step is about Australian settler history, but the chapter label is 'Displacing Indigenous Peoples', which suggests a focus on the indigenous perspective in multiple regions.

### Grade 11 / History / Chapter 6: Displacing Indigenous Peoples — Worked Examples: Displacing Indigenous Peoples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will trace settler expansion, forced removal and the transformation of the North American landscape."
- **Problem:** This step is about settler expansion and forced removal in North America, but the chapter label is 'Displacing Indigenous Peoples', which suggests a focus on the indigenous perspective in multiple regions.

### Grade 11 / History / Chapter 7: Paths to Modernisation — Concept Introduction: Paths to Modernisation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will understand the foundations of Japanese modernisation before the Meiji Restoration."
- **Problem:** This step is about Japanese modernisation, but the chapter label is 'Care and Maintenance of Fabrics'.

### Grade 11 / History / Chapter 7: Paths to Modernisation — Core Explanation: Paths to Modernisation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will explain the Meiji Restoration and Japan’s state-led modernisation."
- **Problem:** This step is about Japanese modernisation, but the chapter label is 'Care and Maintenance of Fabrics'.

### Grade 11 / History / Chapter 7: Paths to Modernisation — Exam-style problems: Paths to Modernisation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will trace China’s search for sovereignty and equality from the Opium War to communist victory."
- **Problem:** This step is about Chinese history, but the chapter label is 'Care and Maintenance of Fabrics'.

### Grade 11 / History / Chapter 7: Paths to Modernisation — Revision and recap: Paths to Modernisation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will evaluate communist rule, market reform, Taiwan and South Korea."
- **Problem:** This step is about East Asian history, but the chapter label is 'Care and Maintenance of Fabrics'.

### Grade 11 / History / Chapter 7: Paths to Modernisation — Worked examples: Paths to Modernisation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will examine debates over Westernisation, everyday social change, war, defeat and Japan’s post-war recovery."
- **Problem:** This step is about Japanese history, but the chapter label is 'Care and Maintenance of Fabrics'.

### Grade 11 / Mathematics / Chapter 4: Complex Numbers and Quadratic Equations — Concept Introduction to Linear Inequalities
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will understand why complex numbers extend the real number system."
- **Problem:** This step is about complex numbers, but the topic is linear inequalities.

### Grade 11 / Mathematics / Chapter 4: Complex Numbers and Quadratic Equations — Lesson on Solving Linear Inequalities in One Variable
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will learn how to solve linear inequalities in one variable algebraically and how to represent their solutions graphically on the number line."
- **Problem:** This step is about solving linear inequalities, but the topic is complex numbers and quadratic equations.

### Grade 11 / Mathematics / Chapter 8: Sequences and Series — Lesson on Equation of a Line: Worked Examples for Class 11 Mathematics
- **Type:** TOPIC_MISMATCH
- **Quote:** "Lesson on Equation of a Line: Worked Examples for Class 11 Mathematics"
- **Problem:** This step's content is about a different chapter/topic than the given chapter label.

### Grade 11 / Physics / Chapter 12: Kinetic Theory — Core Explanation of Thermodynamics
- **Type:** TOPIC_MISMATCH
- **Quote:** "Thermodynamics is the branch of physics that deals with heat, temperature, and energy transfer in systems."
- **Problem:** This step is about thermodynamics, but the chapter label is about Kinetic Theory.

### Grade 11 / Physics / Chapter 12: Kinetic Theory — Worked Example on Work Done by Variable Forces
- **Type:** TOPIC_MISMATCH
- **Quote:** "The woman moving a trunk with a force that decreases linearly from 100 N to 50 N over 20 m"
- **Problem:** This step is about work done by variable forces, but the chapter label is about Kinetic Theory.

### Grade 11 / Physics / Chapter 2: Motion in a Straight Line — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will introduce the concept of units and measurements, focusing on the distinction between average speed and magnitude of average velocity."
- **Problem:** This lesson is about units and measurements, but the chapter label is about motion in a straight line.

### Grade 11 / Physics / Chapter 2: Motion in a Straight Line — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will explore the concept of instantaneous velocity and acceleration, and how they are related to the motion of an object."
- **Problem:** This lesson is about instantaneous velocity and acceleration, but the chapter label is about motion in a straight line.

### Grade 11 / Physics / Chapter 2: Motion in a Straight Line — Exam preparation
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will cover exam-style problems related to units and measurements, specifically focusing on the concepts of average speed, magnitude of average velocity, instantaneous speed, and instantaneous velocity."
- **Problem:** This lesson is about exam preparation for units and measurements, but the chapter label is about motion in a straight line.

### Grade 11 / Physics / Chapter 2: Motion in a Straight Line — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will cover exam-style problems related to units and measurements, specifically focusing on the concepts of average speed, magnitude of average velocity, instantaneous speed, and instantaneous velocity."
- **Problem:** This lesson is about exam-style problems for units and measurements, but the chapter label is about motion in a straight line.

### Grade 11 / Physics / Chapter 2: Motion in a Straight Line — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will revise and recap the key concepts of units and measurements, including the distinction between average speed and magnitude of average velocity, instantaneous speed and magnitude of velocity, and the kinematic equations for uniformly accelerated motion."
- **Problem:** This lesson is about revision and recap for units and measurements, but the chapter label is about motion in a straight line.

### Grade 11 / Physics / Chapter 2: Motion in a Straight Line — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will learn how to solve problems involving uniformly accelerated motion using the kinematic equations."
- **Problem:** This lesson is about worked examples for uniformly accelerated motion, but the chapter label is about motion in a straight line.

### Grade 11 / Physics / Chapter 3: Motion in a Plane — Lesson on Core Concepts of Motion in a Straight Line
- **Type:** TOPIC_MISMATCH
- **Quote:** "When an object moves in a straight line, its position changes over time."
- **Problem:** The chapter label is 'Motion in a Plane', but this lesson step is about motion in a straight line, not motion in a plane.

### Grade 11 / Physics / Chapter 3: Motion in a Plane — Lesson on Physical Quantities: Scalar and Vector Quantities
- **Type:** TOPIC_MISMATCH
- **Quote:** "In physics, quantities describe various aspects of the physical world."
- **Problem:** The chapter label is 'Motion in a Plane', but this lesson step is about scalar and vector quantities in general, not motion in a plane.

### Grade 11 / Physics / Chapter 3: Motion in a Plane — Lesson on Scalar and Vector Quantities in Motion
- **Type:** TOPIC_MISMATCH
- **Quote:** "When an object is projected at an angle, its motion can be split into two parts:"
- **Problem:** The chapter label is 'Motion in a Plane', but this lesson step is about scalar and vector quantities in motion in a straight line, not motion in a plane.

### Grade 11 / Physics / Chapter 3: Motion in a Plane — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "When an object is projected at an angle, its motion can be split into two parts:"
- **Problem:** The chapter label is 'Motion in a Plane', but this lesson step is about projectile motion in a straight line, not motion in a plane.

### Grade 11 / Physics / Chapter 3: Motion in a Plane — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "The following data shows some physical quantities:"
- **Problem:** The chapter label is 'Motion in a Plane', but this lesson step is about scalar and vector quantities in general, not motion in a plane.

### Grade 11 / Physics / Chapter 5: Work, Energy and Power — Concept Introduction to Laws of Motion
- **Type:** TOPIC_MISMATCH
- **Quote:** "Laws of motion explain how objects move and why they move the way they do."
- **Problem:** This step is about the laws of motion, but the chapter label is about work, energy, and power.

### Grade 11 / Physics / Chapter 5: Work, Energy and Power — Core Explanation of Laws of Motion
- **Type:** TOPIC_MISMATCH
- **Quote:** "Laws of motion describe how objects behave when forces act upon them."
- **Problem:** This step is about the laws of motion, but the chapter label is about work, energy, and power.

### Grade 11 / Physics / Chapter 5: Work, Energy and Power — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "In physics, especially in the Laws of Motion, problems often involve multiple forces acting on objects."
- **Problem:** This step is about exam-style problems related to the laws of motion, but the chapter label is about work, energy, and power.

### Grade 11 / Physics / Chapter 5: Work, Energy and Power — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will review the fundamental concepts of Newton's Laws of Motion."
- **Problem:** This step is about the laws of motion, but the chapter label is about work, energy, and power.

### Grade 11 / Physics / Chapter 5: Work, Energy and Power — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "A woman pulls a trunk over a total distance of 20 m. Her applied force reduces linearly from 100 N at 10 m to 50 N at 20 m."
- **Problem:** This step is about work done by variable forces, but the chapter label is about work, energy, and power.

### Grade 11 / Physics / Chapter 7: Gravitation — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will understand the fundamental nature of gravity, why bodies attract each other, and how gravity behaves in different situations."
- **Problem:** This step is about exam-style problems in systems of particles and rotational motion, which is a different topic from the chapter on gravitation.

### Grade 11 / Physics / Chapter 7: Gravitation — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will review the key concepts related to systems of particles and rotational motion, focusing on understanding gravitational effects, the nature of gravitational forces, and how they influence objects at different positions relative to Earth and other celestial bodies."
- **Problem:** This step is about revision and recap of systems of particles and rotational motion, which is a different topic from the chapter on gravitation.

### Grade 11 / Physics / Chapter 7: Gravitation — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "A uniform disc of mass 10 kg and radius 0.5 m is rotating about its central axis with an angular velocity of 20 rad/sec."
- **Problem:** This step is about worked examples in rotational motion, which is a different topic from the chapter on gravitation.

### Grade 11 / Physics / Chapter 8: Mechanical Properties of Solids — Concept Introduction to Gravitation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Gravitation is the force of attraction that all objects in the universe exert on each other."
- **Problem:** This step is about gravitation, but the chapter label is Mechanical Properties of Solids, which is about fluids.

### Grade 11 / Physics / Chapter 8: Mechanical Properties of Solids — Core explanation of Gravitation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Gravitation is a force of attraction that acts between any two objects with mass."
- **Problem:** This step is about gravitation, but the chapter label is Mechanical Properties of Solids, which is about fluids.

### Grade 12 / Accountancy / Chapter 4: Dissolution of Partnership Firm — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "A partnership agreement can change while the business continues, but dissolution of the firm ends the business itself."
- **Problem:** The topic of this step is dissolution of partnership firm, but the content is about dissolution of partnership, which is a different concept.

### Grade 12 / Accountancy / Chapter 6: Issue and Redemption of Debentures — Concept introduction: Issue and Redemption of Debentures
- **Type:** TOPIC_MISMATCH
- **Quote:** "A debenture is a written acknowledgement of company debt."
- **Problem:** This step is about debentures, but the chapter label is about issue and redemption of debentures, which is more about the process of raising and repaying debt, not just the debt instrument itself.

### Grade 12 / Biology / Chapter 3: Reproductive Health — Exam-style problems: Reproductive Health
- **Type:** TOPIC_MISMATCH
- **Quote:** "the chapter stresses that while most are curable if caught early, a few are not — and all are a major threat to a reproductively healthy society"
- **Problem:** The chapter is discussing sexually transmitted infections (STIs), but the topic label is 'Reproductive Health', which is a broader topic.

### Grade 12 / Biology / Chapter 4: Principles of Inheritance and Variation — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "This simple observation — that offspring resemble their parents, yet also show variation — is what genetics, the branch of biology dealing with inheritance and variation of characters, sets out to explain scientifically."
- **Problem:** The chapter is about Principles of Inheritance and Variation, but the content is about genetics in general.

### Grade 12 / Biology / Chapter 4: Principles of Inheritance and Variation — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "This section walks through Mendel's single most famous experiment — crossing tall and dwarf pea plants — and shows how its results led him to propose two fundamental laws of inheritance."
- **Problem:** The chapter is about Principles of Inheritance and Variation, but the content is about Mendel's experiments and laws of inheritance.

### Grade 12 / Biology / Chapter 4: Principles of Inheritance and Variation — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "This section also tackles a very different question: what actually decides whether an offspring becomes male or female?"
- **Problem:** The chapter is about Principles of Inheritance and Variation, but the content is about sex determination.

### Grade 12 / Biology / Chapter 4: Principles of Inheritance and Variation — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Using this tool, the chapter closes by cataloguing the major human genetic disorders: Mendelian disorders caused by a single altered gene, and chromosomal disorders caused by an abnormal number of whole chromosomes."
- **Problem:** The chapter is about Principles of Inheritance and Variation, but the content is about human genetic disorders.

### Grade 12 / Biology / Chapter 4: Principles of Inheritance and Variation — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Mendel crossed pea plants differing in seed colour (yellow Y, dominant; green y, recessive) and seed shape (round R, dominant; wrinkled r, recessive): RRYY x rryy gave an F1 of RrYy (round, yellow)."
- **Problem:** The chapter is about Principles of Inheritance and Variation, but the content is about Mendel's experiments and dihybrid crosses.

### Grade 12 / Biology / Chapter 5: Molecular Basis of Inheritance — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "The previous chapter described 'factors' (genes) controlling inheritance without explaining what they physically are."
- **Problem:** This step is about DNA structure and genetic material, but the previous chapter is about molecular basis of inheritance, not inheritance itself.

### Grade 12 / Biology / Chapter 6: Evolution — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "Evolutionary biology begins before the first organism appeared."
- **Problem:** The chapter is supposed to be about evolution, but the content is about the origin of life.

### Grade 12 / Biology / Chapter 6: Evolution — Geological history and human evolution: Evolution
- **Type:** TOPIC_MISMATCH
- **Quote:** "Human evolution is reconstructed from fossils, anatomy, brain size, behaviour and culture."
- **Problem:** The chapter is supposed to be about evolution, but the content is about human evolution.

### Grade 12 / Biology / Chapter 7: Human Health and Disease — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "Human health depends on physical, mental and social well-being."
- **Problem:** This step's content is about general human health, not specifically about reproductive health as the chapter label suggests.

### Grade 12 / Biology / Chapter 7: Human Health and Disease — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "The immune system protects the body through immediate non-specific barriers and through specific lymphocyte responses."
- **Problem:** This step's content is about the immune system, not specifically about reproductive health.

### Grade 12 / Biology / Chapter 7: Human Health and Disease — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "AIDS is acquired immune deficiency syndrome caused by HIV, an enveloped retrovirus with an RNA genome."
- **Problem:** This step's content is about HIV and AIDS, not specifically about reproductive health.

### Grade 12 / Biology / Chapter 7: Human Health and Disease — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Psychoactive substances alter the nervous system and behaviour."
- **Problem:** This step's content is about substance abuse, not specifically about reproductive health.

### Grade 12 / Biology / Chapter 7: Human Health and Disease — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Immune responses must be directed at genuine threats."
- **Problem:** This step's content is about immune responses, not specifically about reproductive health.

### Grade 12 / Business Studies / Chapter 10: Marketing — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Chapter vocabulary to revise: exchange mechanism; marketing versus selling; marketing functions; consumer products; convenience products; shopping products; channels of distribution."
- **Problem:** This step is about revising vocabulary, which is a different topic from the rest of the chapter, which focuses on marketing concepts and strategies.

### Grade 12 / Business Studies / Chapter 3: Business Environment — Revision and recap: Business Environment
- **Type:** TOPIC_MISMATCH
- **Quote:** "The chapter vocabulary to revise: inter-relatedness; dynamic nature; complexity; relativity; early warning signals; planning and policy; economic environment; technological environment; political environment; legal environment; Industrial Policy 1991; technological change."
- **Problem:** This step is about revising vocabulary related to the business environment, but the chapter label is about the impact of the Industrial Policy, 1991 on business.

### Grade 12 / Business Studies / Chapter 3: Business Environment — Worked examples: Business Environment
- **Type:** TOPIC_MISMATCH
- **Quote:** "The dimensions are separate for analysis but influence one another in practice."
- **Problem:** This step is about distinguishing the five dimensions of the general environment, but the chapter label is about the impact of the Industrial Policy, 1991 on business.

### Grade 12 / Business Studies / Chapter 5: Organising — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Functional structure groups similar jobs into departments and supports specialisation and economies of scale."
- **Problem:** This step is actually about functional and divisional structures, not the core explanation of organising.

### Grade 12 / Business Studies / Chapter 5: Organising — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Formal relationships are designed; informal relationships arise naturally."
- **Problem:** This step is actually about formal and informal organisations, not worked examples of organising.

### Grade 12 / Business Studies / Chapter 8: Controlling — Revision and recap: Controlling
- **Type:** TOPIC_MISMATCH
- **Quote:** "Chapter vocabulary to revise: organisational goals; accuracy of standards; efficient use of resources; employee motivation; order and discipline; coordination; limitations of controlling; quantitative standards; management information system."
- **Problem:** This section is about revising vocabulary related to controlling, but it lists topics from the entire chapter, not just controlling.

### Grade 12 / Business Studies / Chapter 9: Financial Management — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "Finance is required to establish, operate, modernise and expand a business."
- **Problem:** This step's content is about financial management, but the chapter label is 'Where Do Companies Do Their Business?' which is about marketing.

### Grade 12 / Business Studies / Chapter 9: Financial Management — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Working capital finances day-to-day operations and must balance liquidity and profitability."
- **Problem:** This step's content is about working capital, but the chapter label is 'Financial Management' which is about financial management in general.

### Grade 12 / Chemistry / Chapter 4: The d- and f-Block Elements — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "The d-block lies between the s- and p-blocks, while the f-block is displayed separately below the main table."
- **Problem:** This step is about the d- and f-block elements, but it is discussing the position of the d-block in the periodic table, which is a topic from a different chapter.

### Grade 12 / Chemistry / Chapter 4: The d- and f-Block Elements — Worked examples
- **Type:** ARITHMETIC_ERROR
- **Quote:** "μ = √[5(5+2)] = √35 = 5.92 BM."
- **Problem:** The calculation of the magnetic moment is incorrect, as the square root of 35 is not equal to 5.92, but rather approximately 5.916.

### Grade 12 / Chemistry / Chapter 6: Haloalkanes and Haloarenes — Core explanation --- # Preparation and physical properties: Haloalkanes and Haloarenes
- **Type:** TOPIC_MISMATCH
- **Quote:** "Preparation methods work by replacing a group, adding across a multiple bond or generating a reactive aromatic diazonium intermediate."
- **Problem:** This step's content is about haloalkanes and haloarenes, but the chapter label is about haloalkanes and haloarenes, which is a different topic.

### Grade 12 / Chemistry / Chapter 6: Haloalkanes and Haloarenes — Exam-style problems --- # Haloarenes and aromatic substitution: Haloalkanes and Haloarenes
- **Type:** TOPIC_MISMATCH
- **Quote:** "In chlorobenzene, the lone pair on chlorine overlaps with the aromatic ring."
- **Problem:** This step's content is about haloarenes and aromatic substitution, but the chapter label is about haloalkanes and haloarenes, which is a different topic.

### Grade 12 / Chemistry / Chapter 6: Haloalkanes and Haloarenes — Revision and recap --- # Polyhalogen compounds and environmental effects: Haloalkanes and Haloarenes
- **Type:** TOPIC_MISMATCH
- **Quote:** "Polyhalogen compounds became valuable because they are often stable, non-flammable and good solvents or pesticides."
- **Problem:** This step's content is about polyhalogen compounds and environmental effects, but the chapter label is about haloalkanes and haloarenes, which is a different topic.

### Grade 12 / Chemistry / Chapter 6: Haloalkanes and Haloarenes — Worked examples --- # Haloalkane reactions and mechanisms: Haloalkanes and Haloarenes
- **Type:** TOPIC_MISMATCH
- **Quote:** "The polar C–X bond makes the carbon electrophilic and the halide a leaving group."
- **Problem:** This step's content is about haloalkane reactions and mechanisms, but the chapter label is about haloalkanes and haloarenes, which is a different topic.

### Grade 12 / English / Chapter 8: Going Places — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will revise character contrast, metaphorical language, present participles and colloquial speech."
- **Problem:** This step is about revising and recapitulating concepts, but it does not match the topic of the chapter, which is about the story 'Going Places'.

### Grade 12 / Geography / Chapter 11: Land Resources and Agriculture — Exam-style problems: Land Resources and Agriculture
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will review the distribution and characteristics of major crops and connect them with crop seasons, moisture conditions and regional patterns."
- **Problem:** This step's content is more about crop patterns and regional variations than land resources and agriculture, which is the chapter's main topic.

### Grade 12 / Geography / Chapter 17: Geographical Perspective on Selected Issues and Problems — Core explanation: Geographical Perspective on Selected Issues and Problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will study the sources and effects of water pollution and compare the pollution of the Ganga and Yamuna."
- **Problem:** This step is about water pollution, which is a different topic from the chapter label 'Geographical Perspective on Selected Issues and Problems'.

### Grade 12 / Geography / Chapter 3: Human Development — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will distinguish growth from development and understand why economic expansion alone is insufficient."
- **Problem:** This step's content is about distinguishing growth from development, which is not the topic of the given chapter label 'Human Development' but rather a subtopic.

### Grade 12 / Geography / Chapter 3: Human Development — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "International comparisons show that smaller or less wealthy places may outperform larger or richer ones when they invest in health, education, freedom and social opportunity."
- **Problem:** This step's content is about international comparisons and the factors that influence human development, which is not the main topic of the given chapter label 'Human Development' but rather a subtopic.

### Grade 12 / Geography / Chapter 4: Primary Activities — Concept introduction: Primary Activities
- **Type:** TOPIC_MISMATCH
- **Quote:** "Primary activities use resources from land, water, vegetation and minerals."
- **Problem:** This step is about primary activities, but the source text is about secondary activities.

### Grade 12 / Geography / Chapter 4: Primary Activities — Core explanation: Primary Activities
- **Type:** TOPIC_MISMATCH
- **Quote:** "Pastoralism began with animal domestication and now ranges from mobile subsistence herding to permanent scientific ranching for world markets."
- **Problem:** This step is about pastoralism, but the source text is about secondary activities.

### Grade 12 / Geography / Chapter 4: Primary Activities — Exam-style problems: Primary Activities
- **Type:** TOPIC_MISMATCH
- **Quote:** "Dairy farming is highly capital- and labour-intensive and depends on breeding, veterinary care, refrigeration and nearby urban markets."
- **Problem:** This step is about dairy farming, but the source text is about secondary activities.

### Grade 12 / Geography / Chapter 4: Primary Activities — Revision and recap: Primary Activities
- **Type:** TOPIC_MISMATCH
- **Quote:** "The central pattern is a movement from direct subsistence dependence towards specialised, scientific and market-oriented activity, though both forms continue in different regions."
- **Problem:** This step is about primary activities, but the source text is about secondary activities.

### Grade 12 / Geography / Chapter 4: Primary Activities — Worked examples: Primary Activities
- **Type:** TOPIC_MISMATCH
- **Quote:** "Agriculture occurs under varied physical and socio-economic conditions. Its systems range from small subsistence plots to large mechanised farms and specialised plantations."
- **Problem:** This step is about agriculture, but the source text is about secondary activities.

### Grade 12 / Geography / Chapter 5: Secondary Activities — Core explanation --- # Core explanation: Secondary Activities
- **Type:** TOPIC_MISMATCH
- **Quote:** "Industries seek locations where production costs are low and market access is strong."
- **Problem:** This step's content is about tertiary activities, not secondary activities.

### Grade 12 / Geography / Chapter 5: Secondary Activities — Exam-style problems --- # Exam-style problems: Secondary Activities
- **Type:** TOPIC_MISMATCH
- **Quote:** "The same industry can be classified in several ways: by its scale, the input it uses, the product it supplies and who owns it."
- **Problem:** This step's content is about tertiary activities, not secondary activities.

### Grade 12 / Geography / Chapter 5: Secondary Activities — Revision and recap --- # Revision and recap: Secondary Activities
- **Type:** TOPIC_MISMATCH
- **Quote:** "Modern industry is increasingly specialised, research-intensive and geographically concentrated, yet advanced production has also spread to new regions and metropolitan peripheries."
- **Problem:** This step's content is about tertiary activities, not secondary activities.

### Grade 12 / Geography / Chapter 7: Transport and Communication — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will understand why transport and communication are essential to production, exchange and quality of life."
- **Problem:** The topic of this step is 'Transport and Communication', but the source text is about 'International Trade'.

### Grade 12 / Geography / Chapter 7: Transport and Communication — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "The fastest transport and the newest communication systems overcome barriers of distance in different ways."
- **Problem:** The topic of this step is 'Transport and Communication', but the source text is about 'International Trade'.

### Grade 12 / Geography / Chapter 7: Transport and Communication — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Railway networks, gauges and commuter services are examined in this step."
- **Problem:** The topic of this step is 'Transport and Communication', but the source text is about 'International Trade'.

### Grade 12 / Hindi / Chapter 13: Pahalwan Ki Dholak — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "इस चरण में कार्यालय के आरंभिक दृश्य से यशोधर बाबू की पुरानी चाल, अनुशासन और आधुनिक सहकर्मियों से दूरी समझेंगे।"
- **Problem:** यह चरण पहलवान की ढोलक के बारे में नहीं है, बल्कि यशोधर बाबू के बारे में है।

### Grade 12 / Hindi / Chapter 13: Pahalwan Ki Dholak — परीक्षा-शैली समस्याएँ
- **Type:** TOPIC_MISMATCH
- **Quote:** "इस चरण में यशोधर और उनके परिवार के बीच मतभेदों के कारणों का विश्लेषण करेंगे।"
- **Problem:** यह चरण पहलवान की ढोलक के बारे में नहीं है, बल्कि यशोधर बाबू और उनके परिवार के बारे में है।

### Grade 12 / Hindi / Chapter 13: Pahalwan Ki Dholak — पुनरावृत्ति और पुनर्स्मरण
- **Type:** TOPIC_MISMATCH
- **Quote:** "इस चरण में सिल्वर वैडिंग समारोह और ड्रेसिंग गाउन वाले अंतिम प्रसंग का अर्थ समझेंगे।"
- **Problem:** यह चरण पहलवान की ढोलक के बारे में नहीं है, बल्कि सिल्वर वैडिंग समारोह और ड्रेसिंग गाउन वाले अंतिम प्रसंग के बारे में है।

### Grade 12 / Hindi / Chapter 13: Pahalwan Ki Dholak — मूल व्याख्या
- **Type:** TOPIC_MISMATCH
- **Quote:** "इस चरण में किशनदा के प्रति यशोधर की श्रद्धा और उनके जीवन पर पड़े प्रभाव को समझेंगे।"
- **Problem:** यह चरण पहलवान की ढोलक के बारे में नहीं है, बल्कि यशोधर बाबू और किशनदा के बारे में है।

### Grade 12 / Hindi / Chapter 13: Pahalwan Ki Dholak — हल किए गए उदाहरण
- **Type:** TOPIC_MISMATCH
- **Quote:** "“समहाउ इम्प्रॉपर” वाक्यांश का प्रयोग यशोधर बाबू लगभग हर वाक्य के प्रारंभ में तकिया कलाम की तरह करते हैं।"
- **Problem:** यह चरण पहलवान की ढोलक के बारे में नहीं है, बल्कि “समहाउ इम्प्रॉपर” वाक्यांश के बारे में है।

### Grade 12 / History / Chapter 10: Rebels and the Raj: The Revolt of 1857 and Its Representations — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "The revolt began among sepoys but quickly drew in townspeople, peasants, rulers and local leaders, turning military disobedience into a wider challenge to colonial authority."
- **Problem:** This step is about the Revolt of 1857, but the SOURCE_TEXT is about Resource Management and Hospitality.

### Grade 12 / History / Chapter 10: Rebels and the Raj: The Revolt of 1857 and Its Representations — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Rebels often turned to recognised rulers for legitimacy, while ordinary leaders, religious figures and shared fears gave the uprising local energy."
- **Problem:** This step is about the Revolt of 1857, but the SOURCE_TEXT is about Resource Management and Hospitality.

### Grade 12 / History / Chapter 10: Rebels and the Raj: The Revolt of 1857 and Its Representations — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "Rebels did not leave one complete programme, but proclamations and actions reveal a desire to restore familiar authority, defend faith and remove exploitative colonial institutions."
- **Problem:** This step is about the Revolt of 1857, but the SOURCE_TEXT is about Resource Management and Hospitality.

### Grade 12 / History / Chapter 10: Rebels and the Raj: The Revolt of 1857 and Its Representations — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "The British defeated the uprising militarily and represented their violence as justified vengeance, while later nationalist art transformed rebels into heroic symbols."
- **Problem:** This step is about the Revolt of 1857, but the SOURCE_TEXT is about Resource Management and Hospitality.

### Grade 12 / History / Chapter 10: Rebels and the Raj: The Revolt of 1857 and Its Representations — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Awadh's rebellion was broad because colonial annexation disrupted a connected social world in which soldiers, village cultivators, taluqdars and the court depended on one another."
- **Problem:** This step is about the Revolt of 1857, but the SOURCE_TEXT is about Resource Management and Hospitality.

### Grade 12 / History / Chapter 1: Bricks, Beads and Bones: The Harappan Civilisation — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will learn how the Harappan civilisation is dated and identified through archaeological evidence."
- **Problem:** This step is about the Harappan Civilisation, but the chapter label is about Work, Livelihood and Career

### Grade 12 / History / Chapter 1: Bricks, Beads and Bones: The Harappan Civilisation — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will examine Mohenjodaro as a planned urban centre and understand how drainage, domestic architecture and public buildings reveal coordinated planning."
- **Problem:** This step is about Mohenjodaro, but the chapter label is about Work, Livelihood and Career

### Grade 12 / History / Chapter 1: Bricks, Beads and Bones: The Harappan Civilisation — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will analyse procurement networks, overseas contacts, seals, writing and weights. You will also evaluate what these systems suggest about Harappan exchange and authority."
- **Problem:** This step is about Harappan exchange and authority, but the chapter label is about Work, Livelihood and Career

### Grade 12 / History / Chapter 1: Bricks, Beads and Bones: The Harappan Civilisation — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will review explanations for urban decline, the modern discovery of Harappa and the difficulties of archaeological interpretation."
- **Problem:** This step is about Harappan archaeology, but the chapter label is about Work, Livelihood and Career

### Grade 12 / History / Chapter 1: Bricks, Beads and Bones: The Harappan Civilisation — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will study social differentiation, craft production and methods of identifying workshops. You will learn how archaeologists move from artefacts to cautious interpretations."
- **Problem:** This step is about Harappan archaeology, but the chapter label is about Work, Livelihood and Career

### Grade 12 / History / Chapter 2: Kings, Farmers and Towns: Early States and Economies — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will learn how epigraphists opened a new window onto early Indian history and how the mahajanapadas developed as early states."
- **Problem:** This step is about epigraphy and mahajanapadas, but the chapter label is about Kings, Farmers and Towns: Early States and Economies, which is about a broader topic.

### Grade 12 / History / Chapter 2: Kings, Farmers and Towns: Early States and Economies — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will examine the Mauryan Empire, its sources, political centres and forms of administration, as well as the limits of imperial control."
- **Problem:** This step is about the Mauryan Empire, but the chapter label is about Kings, Farmers and Towns: Early States and Economies, which is about a broader topic.

### Grade 12 / History / Chapter 2: Kings, Farmers and Towns: Early States and Economies — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will analyse changing agricultural production, rural inequality, land grants and the relationship between cultivators and the state."
- **Problem:** This step is about agricultural production and land grants, but the chapter label is about Kings, Farmers and Towns: Early States and Economies, which is about a broader topic.

### Grade 12 / History / Chapter 2: Kings, Farmers and Towns: Early States and Economies — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will connect urbanisation, craft production, long-distance trade, coinage and the methods and limits of epigraphy."
- **Problem:** This step is about urbanisation and epigraphy, but the chapter label is about Kings, Farmers and Towns: Early States and Economies, which is about a broader topic.

### Grade 12 / History / Chapter 2: Kings, Farmers and Towns: Early States and Economies — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will compare post-Mauryan ideas of kingship, including chiefs, divine claims, samantas and prashastis."
- **Problem:** This step is about post-Mauryan kingship, but the chapter label is about Kings, Farmers and Towns: Early States and Economies, which is about a broader topic.

### Grade 12 / History / Chapter 3: Kinship, Caste and Class: Early Societies — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will understand how historians use the Mahabharata and other textual traditions as evidence."
- **Problem:** This step is about the use of the Mahabharata as historical evidence, but the chapter label is about Kinship, Caste and Class: Early Societies.

### Grade 12 / History / Chapter 3: Kinship, Caste and Class: Early Societies — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will examine family, patriliny, marriage, gotra and the evidence that elite practices could diverge from Brahmanical rules."
- **Problem:** This step is about family and kinship, but the chapter label is about Kinship, Caste and Class: Early Societies.

### Grade 12 / History / Chapter 4: Thinkers, Beliefs and Buildings: Cultural Developments — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will learn why the mid-first millennium BCE was a period of intense philosophical debate and how historians reconstruct traditions from texts and material remains."
- **Problem:** The chapter label is 'Thinkers, Beliefs and Buildings: Cultural Developments' but the topic is about food processing and technology, not philosophical debate.

### Grade 12 / History / Chapter 4: Thinkers, Beliefs and Buildings: Cultural Developments — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will compare the central teachings of Jainism and Buddhism and understand how their teachings were transmitted."
- **Problem:** The chapter label is 'Thinkers, Beliefs and Buildings: Cultural Developments' but the topic is about food processing and technology, not Jainism and Buddhism.

### Grade 12 / History / Chapter 4: Thinkers, Beliefs and Buildings: Cultural Developments — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will analyse why stupas were built, how they were funded and structured, and how historians interpret Buddhist sculpture."
- **Problem:** The chapter label is 'Thinkers, Beliefs and Buildings: Cultural Developments' but the topic is about food processing and technology, not Buddhist sculpture.

### Grade 12 / History / Chapter 4: Thinkers, Beliefs and Buildings: Cultural Developments — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will trace the preservation of Sanchi and destruction of Amaravati, the rise of Mahayana and Puranic traditions, temple architecture and the limits of interpreting visual evidence."
- **Problem:** The chapter label is 'Thinkers, Beliefs and Buildings: Cultural Developments' but the topic is about food processing and technology, not Sanchi, Amaravati, or Mahayana and Puranic traditions.

### Grade 12 / History / Chapter 4: Thinkers, Beliefs and Buildings: Cultural Developments — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will study the Buddhist sangha, equality within monastic life, the entry of women and the reasons Buddhism attracted diverse followers."
- **Problem:** The chapter label is 'Thinkers, Beliefs and Buildings: Cultural Developments' but the topic is about food processing and technology, not the Buddhist sangha.

### Grade 12 / History / Chapter 5: Through the Eyes of Travellers: Perceptions of Society — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will meet three travellers from different centuries and understand why their accounts describe India in different ways."
- **Problem:** This step is about travel writing, but the chapter label is 'Through the Eyes of Travellers: Perceptions of Society', which suggests a focus on historical perceptions of society, not travel writing.

### Grade 12 / History / Chapter 5: Through the Eyes of Travellers: Perceptions of Society — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will examine the structure of Al-Biruni's Kitab-ul-Hind, his methods and his analysis of caste."
- **Problem:** This step is about Al-Biruni's Kitab-ul-Hind, but the chapter label is 'Through the Eyes of Travellers: Perceptions of Society', which suggests a focus on historical perceptions of society, not Al-Biruni's work.

### Grade 12 / History / Chapter 5: Through the Eyes of Travellers: Perceptions of Society — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will evaluate Bernier's picture of Mughal landownership, cities and craft production and understand how his European comparisons produced both insights and distortions."
- **Problem:** This step is about Bernier's account, but the chapter label is 'Through the Eyes of Travellers: Perceptions of Society', which suggests a focus on historical perceptions of society, not Bernier's account.

### Grade 12 / History / Chapter 5: Through the Eyes of Travellers: Perceptions of Society — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will review evidence about slavery, women and sati and practise distinguishing a traveller's observation from a general claim about society."
- **Problem:** This step is about reviewing evidence, but the chapter label is 'Through the Eyes of Travellers: Perceptions of Society', which suggests a focus on historical perceptions of society, not reviewing evidence.

### Grade 12 / History / Chapter 5: Through the Eyes of Travellers: Perceptions of Society — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will reconstruct urban life through Ibn Battuta's observations of cities, markets, agriculture, travel and communication."
- **Problem:** This step is about Ibn Battuta's observations, but the chapter label is 'Through the Eyes of Travellers: Perceptions of Society', which suggests a focus on historical perceptions of society, not Ibn Battuta's observations.

### Grade 12 / History / Chapter 6: Bhakti-Sufi Traditions: Changes in Religious Beliefs and Devotional Texts — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will understand the mosaic of religious beliefs in medieval India and the processes through which local cults interacted with wider Puranic traditions."
- **Problem:** The chapter topic is Bhakti-Sufi Traditions: Changes in Religious Beliefs and Devotional Texts, but the content is about Human Development and Family Studies.

### Grade 12 / History / Chapter 6: Bhakti-Sufi Traditions: Changes in Religious Beliefs and Devotional Texts — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will study the Alvars, Nayanars and Virashaivas and examine how devotion created new religious communities and critiques of caste and gender norms."
- **Problem:** The chapter topic is Bhakti-Sufi Traditions: Changes in Religious Beliefs and Devotional Texts, but the content is about Human Development and Family Studies.

### Grade 12 / History / Chapter 6: Bhakti-Sufi Traditions: Changes in Religious Beliefs and Devotional Texts — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will study the Chishtis, their devotional life, relationship with rulers and use of languages, music and pilgrimage."
- **Problem:** The chapter topic is Bhakti-Sufi Traditions: Changes in Religious Beliefs and Devotional Texts, but the content is about Human Development and Family Studies.

### Grade 12 / History / Chapter 6: Bhakti-Sufi Traditions: Changes in Religious Beliefs and Devotional Texts — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will compare Kabir, Baba Guru Nanak and Mirabai and learn how historians reconstruct traditions from poems, conversations, letters and hagiographies."
- **Problem:** The chapter topic is Bhakti-Sufi Traditions: Changes in Religious Beliefs and Devotional Texts, but the content is about Human Development and Family Studies.

### Grade 12 / History / Chapter 6: Bhakti-Sufi Traditions: Changes in Religious Beliefs and Devotional Texts — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will examine the arrival and localisation of Islam, the growth of Sufism, and the organisation of khanqahs and silsilas."
- **Problem:** The chapter topic is Bhakti-Sufi Traditions: Changes in Religious Beliefs and Devotional Texts, but the content is about Human Development and Family Studies.

### Grade 12 / History / Chapter 7: An Imperial Capital: Vijayanagara — Concept introduction: An Imperial Capital: Vijayanagara
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will learn how Hampi was rediscovered and how historians combine different sources to reconstruct Vijayanagara."
- **Problem:** This step is about the history of Vijayanagara, but the chapter label is about the management of support services, institutions, and programmes for children, youth, and the elderly.

### Grade 12 / History / Chapter 7: An Imperial Capital: Vijayanagara — Core explanation: An Imperial Capital: Vijayanagara
- **Type:** TOPIC_MISMATCH
- **Quote:** "Vijayanagara's power rested on warfare, commerce and delegated military authority, but the same powerful chiefs who supported expansion could weaken the centre."
- **Problem:** This step is about the history of Vijayanagara, but the chapter label is about the management of support services, institutions, and programmes for children, youth, and the elderly.

### Grade 12 / History / Chapter 7: An Imperial Capital: Vijayanagara — Exam-style problems: An Imperial Capital: Vijayanagara
- **Type:** TOPIC_MISMATCH
- **Quote:** "The royal centre was not simply a residential palace quarter; it contained temples, platforms, halls, tanks and structures used for political and ceremonial display."
- **Problem:** This step is about the history of Vijayanagara, but the chapter label is about the management of support services, institutions, and programmes for children, youth, and the elderly.

### Grade 12 / History / Chapter 7: An Imperial Capital: Vijayanagara — Revision and recap: An Imperial Capital: Vijayanagara
- **Type:** TOPIC_MISMATCH
- **Quote:** "Vijayanagara's planners used the Tungabhadra basin and granite hills to organise water, defence, cultivation and movement across a vast urban landscape."
- **Problem:** This step is about the history of Vijayanagara, but the chapter label is about the management of support services, institutions, and programmes for children, youth, and the elderly.

### Grade 12 / History / Chapter 7: An Imperial Capital: Vijayanagara — Worked examples: An Imperial Capital: Vijayanagara
- **Type:** TOPIC_MISMATCH
- **Quote:** "Vijayanagara's planners used the Tungabhadra basin and granite hills to organise water, defence, cultivation and movement across a vast urban landscape."
- **Problem:** This step is about the history of Vijayanagara, but the chapter label is about the management of support services, institutions, and programmes for children, youth, and the elderly.

### Grade 12 / History / Chapter 8: Peasants, Zamindars and the State: Agrarian Society and the Mughal Empire — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will learn how historians reconstruct Mughal agrarian society and why the Ain-i Akbari must be read with other sources."
- **Problem:** The chapter label is 'Peasants, Zamindars and the State: Agrarian Society and the Mughal Empire', but the content is about 'Fabric and Apparel'.

### Grade 12 / History / Chapter 8: Peasants, Zamindars and the State: Agrarian Society and the Mughal Empire — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Mughal agriculture aimed to feed households but was also deeply connected to taxation, markets and the production of high-value crops."
- **Problem:** The chapter label is 'Peasants, Zamindars and the State: Agrarian Society and the Mughal Empire', but the content is about 'Fabric and Apparel'.

### Grade 12 / History / Chapter 8: Peasants, Zamindars and the State: Agrarian Society and the Mughal Empire — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "The agrarian frontier expanded into forests through negotiation, migration, force and commerce, while zamindars linked local society with the imperial state."
- **Problem:** The chapter label is 'Peasants, Zamindars and the State: Agrarian Society and the Mughal Empire', but the content is about 'Fabric and Apparel'.

### Grade 12 / History / Chapter 8: Peasants, Zamindars and the State: Agrarian Society and the Mughal Empire — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Agrarian production became imperial revenue through measurement, assessment and collection, while expanding money use linked villages to a wider commercial world."
- **Problem:** The chapter label is 'Peasants, Zamindars and the State: Agrarian Society and the Mughal Empire', but the content is about 'Fabric and Apparel'.

### Grade 12 / History / Chapter 8: Peasants, Zamindars and the State: Agrarian Society and the Mughal Empire — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "The village was neither an equal republic nor only a collection of individual farms: it contained collective institutions, occupational interdependence and deep inequalities."
- **Problem:** The chapter label is 'Peasants, Zamindars and the State: Agrarian Society and the Mughal Empire', but the content is about 'Fabric and Apparel'.

### Grade 12 / History / Chapter 9: Colonialism and the Countryside: Exploring Official Archives — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will learn why the Permanent Settlement produced auctions, defaults and new struggles for rural power in Bengal."
- **Problem:** The topic of this step is Colonialism and the Countryside: Exploring Official Archives, but the content is about the Permanent Settlement in Bengal, which is a different topic.

### Grade 12 / History / Chapter 9: Colonialism and the Countryside: Exploring Official Archives — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will compare the livelihoods of Paharias and Santhals and understand how colonial surveys and agrarian expansion transformed the Rajmahal hills."
- **Problem:** The topic of this step is Colonialism and the Countryside: Exploring Official Archives, but the content is about the Paharias and Santhals in the Rajmahal hills, which is a different topic.

### Grade 12 / History / Chapter 9: Colonialism and the Countryside: Exploring Official Archives — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will trace the cotton boom during the American Civil War and explain why prosperity was followed by a credit crisis."
- **Problem:** The topic of this step is Colonialism and the Countryside: Exploring Official Archives, but the content is about the American Civil War and the cotton boom, which is a different topic.

### Grade 12 / History / Chapter 9: Colonialism and the Countryside: Exploring Official Archives — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will evaluate the Fifth Report, Buchanan's accounts and the Deccan Riots Commission as official sources."
- **Problem:** The topic of this step is Colonialism and the Countryside: Exploring Official Archives, but the content is about evaluating official sources, which is a different topic.

### Grade 12 / History / Chapter 9: Colonialism and the Countryside: Exploring Official Archives — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will examine the ryotwari system, debt and the economic chain that produced the Deccan riots of 1875."
- **Problem:** The topic of this step is Colonialism and the Countryside: Exploring Official Archives, but the content is about the ryotwari system and the Deccan riots, which is a different topic.

### Grade 12 / Mathematics / Chapter 13: Probability — Revision and recap --- # Revision and recap: Probability
- **Type:** TOPIC_MISMATCH
- **Quote:** "A random variable is a real-valued function on the sample space."
- **Problem:** This statement is not relevant to the topic of conditional probability and is actually a definition of a random variable, which is discussed later in the chapter.

### Grade 12 / Mathematics / Chapter 13: Probability — Worked examples --- # Worked examples: Probability
- **Type:** TOPIC_MISMATCH
- **Quote:** "If X is the number of heads in two coin tosses, what values does X assign to HH, HT, TH and TT?"
- **Problem:** This question is actually about random variables and is not relevant to the topic of conditional probability.

### Grade 12 / Mathematics / Chapter 5: Continuity and Differentiability — Exam-style problems: Continuity and Differentiability
- **Type:** TOPIC_MISMATCH
- **Quote:** "When x and y are both functions of a parameter t, dy/dx is the ratio (dy/dt)/(dx/dt)."
- **Problem:** This step appears to be discussing parametric differentiation, which is not the topic of the current chapter.

### Grade 12 / Mathematics / Chapter 5: Continuity and Differentiability — Revision and recap: Continuity and Differentiability
- **Type:** TOPIC_MISMATCH
- **Quote:** "Mean value theorems connect an average change over an interval with an instantaneous derivative at some interior point."
- **Problem:** This step appears to be discussing mean value theorems, which are not the topic of the current chapter.

### Grade 12 / Mathematics / Chapter 8: Application of Integrals — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "A periodic curve may lie above and below the x-axis."
- **Problem:** This step is discussing the topic of periodic curves, which is not relevant to the chapter on Application of Integrals.

### Grade 12 / Physics / Chapter 10: Wave Optics — Worked Example on Work Done in Electrostatics
- **Type:** TOPIC_MISMATCH
- **Quote:** "This step is about work done in electrostatics, which is a different topic."
- **Problem:** This step is not related to wave optics.

### Grade 12 / Physics / Chapter 11: Dual Nature of Radiation and Matter — Lesson on Coulomb’s Law and Electrostatic Forces
- **Type:** TOPIC_MISMATCH
- **Quote:** "The lesson is about Coulomb’s Law and electrostatic forces, which is a different topic from the dual nature of radiation and matter."
- **Problem:** The lesson is not about the dual nature of radiation and matter.

### Grade 12 / Physics / Chapter 11: Dual Nature of Radiation and Matter — Worked Example on Coulomb’s Law and Electrostatic Force
- **Type:** TOPIC_MISMATCH
- **Quote:** "The lesson is about Coulomb’s Law and electrostatic force, which is a different topic from the dual nature of radiation and matter."
- **Problem:** The lesson is not about the dual nature of radiation and matter.

### Grade 12 / Physics / Chapter 12: Atoms — Core Explanation of Atoms
- **Type:** TOPIC_MISMATCH
- **Quote:** "This lesson revisits the core ideas about atoms, including their structure, charge distribution, and the forces involved."
- **Problem:** This lesson is supposed to be about the core explanation of atoms, but it covers a broader range of topics, including atomic structure, charge distribution, and forces involved.

### Grade 12 / Physics / Chapter 12: Atoms — Lesson on Coulomb’s Law and Electrostatic Force between Two Charges
- **Type:** TOPIC_MISMATCH
- **Quote:** "This lesson will cover Coulomb’s law, the force between two charges, and its applications."
- **Problem:** This lesson is supposed to be about Coulomb’s law and electrostatic force, but it covers a broader range of topics, including the significance of the inverse-square law and practical applications.

### Grade 12 / Physics / Chapter 12: Atoms — Revision and recap of Atoms (Class 12 CBSE Physics)
- **Type:** TOPIC_MISMATCH
- **Quote:** "This lesson revisits the core ideas about atoms, including their structure, charge distribution, and the forces involved."
- **Problem:** This lesson is supposed to be a revision and recap of atoms, but it covers a broader range of topics, including Coulomb’s law, electric fields, and atomic models.

### Grade 12 / Physics / Chapter 12: Atoms — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "This lesson will cover worked examples of atomic spectra and Bohr’s postulates."
- **Problem:** This lesson is supposed to be about worked examples, but it covers a broader range of topics, including atomic spectra and Bohr’s postulates.

### Grade 12 / Physics / Chapter 3: Current Electricity — Core explanation --- # Core Explanation of Current Electricity
- **Type:** TOPIC_MISMATCH
- **Quote:** "In current electricity, Kirchhoff’s laws are fundamental for analyzing complex circuits."
- **Problem:** This step is about Kirchhoff’s laws, which is a topic from Chapter 4, not Chapter 3.

### Grade 12 / Physics / Chapter 3: Current Electricity — Exam-style problems --- # Lesson on Exam-Style Problems in Current Electricity
- **Type:** TOPIC_MISMATCH
- **Quote:** "In current electricity, Kirchhoff’s laws are fundamental for analyzing complex circuits."
- **Problem:** This step is about Kirchhoff’s laws, which is a topic from Chapter 4, not Chapter 3.

### Grade 12 / Physics / Chapter 3: Current Electricity — Revision and recap --- # Current Electricity: Revision and Recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "In current electricity, Kirchhoff’s rules—Kirchhoff’s current law (KCL) and Kirchhoff’s voltage law (KVL)—help us set up equations based on the conservation of charge and energy."
- **Problem:** This step is about Kirchhoff’s laws, which is a topic from Chapter 4, not Chapter 3.

### Grade 12 / Physics / Chapter 3: Current Electricity — Worked examples --- # Current Electricity: Worked Examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "In current electricity, Kirchhoff’s rules—Kirchhoff’s current law (KCL) and Kirchhoff’s voltage law (KVL)—help us set up equations based on the conservation of charge and energy."
- **Problem:** This step is about Kirchhoff’s laws, which is a topic from Chapter 4, not Chapter 3.

### Grade 12 / Physics / Chapter 5: Magnetism and Matter — Torque on a magnetic dipole: Chapter 5: Magnetism and Matter
- **Type:** ARITHMETIC_ERROR
- **Quote:** "m = τ/(B sinθ). m = 4.5 × 10⁻²/[0.25 × sin30°]."
- **Problem:** The calculation for m is incorrect, and the correct calculation should be m = 4.5 × 10⁻²/[0.25 × 1] = 18.

### Grade 12 / Physics / Chapter 8: Electromagnetic Waves — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will explain Maxwell’s correction and calculate displacement current in a charging capacitor."
- **Problem:** The step's content is about displacement current, which is not the main topic of Chapter 8: Electromagnetic Waves.

### Grade 12 / Physics / Chapter 9: Ray Optics and Optical Instruments — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will understand the concept of electric dipoles, how their electric fields behave at different points in space, and how the potential due to a dipole is different from that of a single charge."
- **Problem:** The topic is about electric dipoles, not ray optics and optical instruments.

### Grade 12 / Political Science / Chapter 10: Politics of Planned Development — Planning Commission, Bombay Plan and Five Year Plans
- **Type:** TOPIC_MISMATCH
- **Quote:** "The Planning Commission was created by a government resolution in March 1950, not directly by the Constitution, and the Prime Minister served as chairperson."
- **Problem:** The SOURCE_TEXT does not mention the Planning Commission, but the lesson step discusses it as if it is a major topic of the chapter, which is not the case.

### Grade 12 / Political Science / Chapter 11: India's External Relations — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "India framed policy in a divided and rapidly changing world."
- **Problem:** The topic of this step is supposed to be India's External Relations, but it seems to be about India's foreign policy in general, not specifically about external relations.

### Grade 12 / Political Science / Chapter 11: India's External Relations — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "India supported Indonesian freedom, opposed apartheid and convened Asian meetings."
- **Problem:** The topic of this step is supposed to be non-alignment, but it seems to be about India's foreign policy in general, not specifically about non-alignment.

### Grade 12 / Political Science / Chapter 11: India's External Relations — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "The conflict exposed the limits of optimistic diplomacy."
- **Problem:** The topic of this step is supposed to be the movement from early friendship with China to border war, but it seems to be about the general conflict between India and China, not specifically about the movement from friendship to war.

### Grade 12 / Political Science / Chapter 11: India's External Relations — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "The 1974 test changed India’s strategic profile."
- **Problem:** The topic of this step is supposed to be nuclear policy and domestic consensus, but it seems to be about the 1974 nuclear test, not specifically about nuclear policy and domestic consensus.

### Grade 12 / Political Science / Chapter 11: India's External Relations — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "The conflict exposed the limits of optimistic diplomacy."
- **Problem:** The topic of this step is supposed to be the movement from early friendship with China to border war, but it seems to be about the general conflict between India and China, not specifically about the movement from friendship to war.

### Grade 12 / Political Science / Chapter 13: The Crisis of Democratic Order — Core explanation: The Crisis of Democratic Order
- **Type:** TOPIC_MISMATCH
- **Quote:** "The constitutional crisis centred on how far Parliament could amend the Constitution and restrict rights."
- **Problem:** This step discusses the constitutional crisis, but the chapter label is about the crisis of democratic order, which seems to be more related to regional aspirations and the challenges of nation-building.

### Grade 12 / Political Science / Chapter 13: The Crisis of Democratic Order — Revision and recap: The Crisis of Democratic Order
- **Type:** TOPIC_MISMATCH
- **Quote:** "The Janata coalition was broad but internally divided."
- **Problem:** This step discusses the Janata government, but the chapter label is about the crisis of democratic order, which seems to be more related to regional aspirations and the challenges of nation-building.

### Grade 12 / Political Science / Chapter 14: Regional Aspirations — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "The focus is on Kashmiriyat, accession, autonomy, democratic dissatisfaction and insurgency."
- **Problem:** This step's content is about the Jammu and Kashmir issue, which is a different topic than regional aspirations.

### Grade 12 / Political Science / Chapter 14: Regional Aspirations — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will compare autonomy, secession and outsider movements in the North-East."
- **Problem:** This step's content is about the North-East region, which is a different topic than regional aspirations.

### Grade 12 / Political Science / Chapter 14: Regional Aspirations — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will revise Sikkim, Goa and the chapter’s general lessons on national integration."
- **Problem:** This step's content is about Sikkim and Goa, which are different topics than regional aspirations.

### Grade 12 / Political Science / Chapter 14: Regional Aspirations — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will trace the Punjab crisis from autonomy demands to violence and negotiated settlement."
- **Problem:** This step's content is about the Punjab crisis, which is a different topic than regional aspirations.

### Grade 12 / Political Science / Chapter 2: Contemporary Centres of Power — Concept introduction: Contemporary Centres of Power
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will understand how the European Union emerged from Europe’s post-war destruction and old rivalries."
- **Problem:** This step is about the European Union, not the chapter label 'Contemporary Centres of Power'.

### Grade 12 / Political Science / Chapter 2: Contemporary Centres of Power — Exam-style problems: Contemporary Centres of Power
- **Type:** TOPIC_MISMATCH
- **Quote:** "India and China are both major Asian powers, but their modern relationship has combined border disputes and strategic mistrust with expanding diplomatic, economic and institutional cooperation."
- **Problem:** This step is about India and China, not the chapter label 'Contemporary Centres of Power'.

### Grade 12 / Political Science / Chapter 2: Contemporary Centres of Power — Revision and recap: Contemporary Centres of Power
- **Type:** TOPIC_MISMATCH
- **Quote:** "The post-bipolar world contains several important centres of influence. The EU and ASEAN derive power from regional organisation; China combines size, state-guided reform and global economic integration; Japan and South Korea combine advanced industry, technology, trade and strong institutions."
- **Problem:** This step is about various centres of power, not the chapter label 'Contemporary Centres of Power'.

### Grade 12 / Political Science / Chapter 2: Contemporary Centres of Power — Worked examples: Contemporary Centres of Power
- **Type:** TOPIC_MISMATCH
- **Quote:** "China’s rise as a centre of power came from economic reforms begun in the 1970s. Unlike post-Soviet shock therapy, China opened its economy step by step, combined market mechanisms with a continuing state role, and used foreign investment and Special Economic Zones to expand production and trade."
- **Problem:** This step is about China, not the chapter label 'Contemporary Centres of Power'.

### Grade 12 / Political Science / Chapter 3: Contemporary South Asia — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "Defining the region and its democratic aspiration: Contemporary South Asia"
- **Problem:** The chapter label is Grade 12 / Political Science / Chapter 3: Contemporary South Asia, but the content is about South Asia's political systems and democratic aspiration, which is not the same chapter.

### Grade 12 / Political Science / Chapter 6: Environment and Natural Resources — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "Environmental damage affects food, water, health, livelihoods and future development."
- **Problem:** This step is about environmental concerns becoming global politics, but the chapter is actually about challenges of nation-building in India since independence.

### Grade 12 / Political Science / Chapter 6: Environment and Natural Resources — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Some areas lie outside the jurisdiction of any one state and require common governance."
- **Problem:** This step is about global commons and differentiated responsibility, but the chapter is actually about challenges of nation-building in India since independence.

### Grade 12 / Political Science / Chapter 6: Environment and Natural Resources — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "Environmental movements are diverse rather than a single unified campaign."
- **Problem:** This step is about environmental movements and competing ideas of development, but the chapter is actually about challenges of nation-building in India since independence.

### Grade 12 / Political Science / Chapter 6: Environment and Natural Resources — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Natural resources are not distributed evenly."
- **Problem:** This step is about resource geopolitics and indigenous peoples, but the chapter is actually about challenges of nation-building in India since independence.

### Grade 12 / Political Science / Chapter 6: Environment and Natural Resources — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Common property resources belong to a group whose members possess both rights and duties."
- **Problem:** This step is about common property resources and India’s environmental position, but the chapter is actually about challenges of nation-building in India since independence.

### Grade 12 / Political Science / Chapter 9: Era of One-Party Dominance — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "Building democracy through the first general election: Era of One-Party Dominance"
- **Problem:** This step's content is about the first general election, but the chapter label is Era of One-Party Dominance, which suggests a broader topic.

### Grade 12 / Political Science / Chapter 9: Era of One-Party Dominance — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Congress victories and the electoral system: Era of One-Party Dominance"
- **Problem:** This step's content is about Congress victories and the electoral system, but the chapter label is Era of One-Party Dominance, which suggests a broader topic.

### Grade 12 / Political Science / Chapter 9: Era of One-Party Dominance — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "Opposition parties and their ideological alternatives: Era of One-Party Dominance"
- **Problem:** This step's content is about opposition parties and their ideological alternatives, but the chapter label is Era of One-Party Dominance, which suggests a broader topic.

### Grade 5 / EVS / Chapter 3: The Mystery of Food — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will learn how people select fresh produce and why seasonal and local foods are valued."
- **Problem:** This step is about selecting fresh produce and the value of seasonal and local foods, which is not the main topic of Chapter 3: The Mystery of Food.

### Grade 5 / EVS / Chapter 3: The Mystery of Food — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will identify the jobs of different teeth and explain how chewing and saliva help digestion."
- **Problem:** This step is about teeth, digestion, oral hygiene, and safe eating, which is not the main topic of Chapter 3: The Mystery of Food.

### Grade 5 / EVS / Chapter 5: Our Vibrant Country — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "Even similar musical instruments can look and sound different across regions."
- **Problem:** This step's content is about music and dance, but it does not match the topic of the chapter, which is about India's diversity and culture.

### Grade 5 / EVS / Chapter 5: Our Vibrant Country — Music, Dance and Local Materials
- **Type:** TOPIC_MISMATCH
- **Quote:** "Even similar musical instruments can look and sound different across regions."
- **Problem:** This step's content is about music and dance, but it does not match the topic of the chapter, which is about India's diversity and culture.

### Grade 5 / EVS / Chapter 6: Some Unique Places — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "The Western Ghats are a long chain of forested hills with rich life."
- **Problem:** The chapter is supposed to be about the Sundarbans and mangrove adaptations, but this step is about the Western Ghats.

### Grade 5 / EVS / Chapter 6: Some Unique Places — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "The chapter concludes that the country is rich, beautiful and connected."
- **Problem:** The chapter is supposed to be about the Sundarbans and mangrove adaptations, but this step is about the Northeast and Western Ghats.

### Grade 5 / EVS / Chapter 6: Some Unique Places — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Suppose you want to learn about the mangrove forest in the Sundarbans:"
- **Problem:** The chapter is supposed to be about the Sundarbans and mangrove adaptations, but this step is about the Northeast and Western Ghats.

### Grade 5 / EVS / Chapter 9: Rhythms of Nature — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "This lesson, we will understand what we have learned about the patterns and changes in nature throughout the year."
- **Problem:** This step's content is not about Chapter 9: Rhythms of Nature, but rather a general recap of the unit.

### Grade 5 / English / 1. Papa's Spectacles — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "The language tasks ask learners to compare sizes, weights, and numbers, complete pair phrases, and choose correctly spelt words."
- **Problem:** This step is about ascending order, number order, pair phrases, and spelling, which is a different topic from the poem 'Papa's Spectacles'.

### Grade 5 / English / 10. Glass Bangles — Exam-style problems
- **Type:** ARITHMETIC_ERROR
- **Quote:** "Question: Why is bangle making described as skilled work?"
- **Problem:** The final answer is mathematically incorrect: 'Each stage needs control and attention to produce a strong, attractive bangle.'

### Grade 5 / English / 10. Glass Bangles — Worked examples
- **Type:** ARITHMETIC_ERROR
- **Quote:** "Question: If Ravi makes 50 bangles a day, and each takes about 15 minutes, he can produce around 200 bangles in a day."
- **Problem:** The calculation is mathematically incorrect: 50 bangles/day * 15 minutes/bangle = 750 minutes/day, not 200 bangles/day.

### Grade 5 / English / 5. The Frog — Lesson on 'Where Does the Frog Like to Sit or Spend Time?'
- **Type:** TOPIC_MISMATCH
- **Quote:** "Frogs catch their food using their quick tongue, move by jumping and swimming, and hide among plants and leaves with their matching colors."
- **Problem:** This step is about a different topic than the given chapter label '5. The Frog'.

### Grade 5 / English / 9. Vocation — Lesson on Recap of Common Errors in Sentences
- **Type:** TOPIC_MISMATCH
- **Quote:** "How to identify common grammatical errors in sentences."
- **Problem:** This step is about grammar and sentence correction, which is a different topic from the chapter's focus on vocations and work.

### Grade 5 / Maths / Chapter 5: Far and Near — Exam-Style Problems: Far and Near
- **Type:** ARITHMETIC_ERROR
- **Quote:** "For `3 km 450 m + 4 km 650 m`, add kilometres and metres separately."
- **Problem:** The calculation `3 km 450 m + 4 km 650 m = 8 km 100 m` is incorrect. The correct calculation is `3,450 m + 4,650 m = 8,100 m = 8 km 100 m`.

### Grade 5 / Maths / Chapter 6: The Dairy Farm — Exam-style problems: The Dairy Farm
- **Type:** FABRICATED_NUMBER
- **Quote:** "For 453 × 13, the partial products are 3 × 453 = 1,359 and 10 × 453 = 4,530."
- **Problem:** The numbers 1,359 and 4,530 do not appear in the source text and are not well-known constants.

### Grade 5 / Maths / Chapter 6: The Dairy Farm — Exam-style problems: The Dairy Farm
- **Type:** ARITHMETIC_ERROR
- **Quote:** "For 453 × 13, the chapter calculates products for 5 ones, 2 tens, and 1 hundred before adding them."
- **Problem:** The calculation for 453 × 13 is incorrect and does not match the source text.

### Grade 5 / Maths / Chapter 6: The Dairy Farm — Worked examples: The Dairy Farm
- **Type:** FABRICATED_NUMBER
- **Quote:** "For 69 × 45, the chapter combines 5 × 69 and 40 × 69."
- **Problem:** The numbers 5 and 40 do not appear in the source text and are not well-known constants.

### Grade 5 / Maths / Chapter 9: Coconut Farm — Exam-style problems: Coconut Farm
- **Type:** TOPIC_MISMATCH
- **Quote:** "This step's content is about division using place value and regrouping, which is not the main topic of this chapter."
- **Problem:** This step's content is about a different topic than the given chapter label.

### Grade 6 / English / Unit 1: Fables and Folk Tales — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will read The Raven and the Fox as a fable and explain how flattery causes the Raven's loss."
- **Problem:** This step's content is about a different chapter/topic, The Raven and the Fox, not the given chapter label, A Bottle of Dew.

### Grade 6 / English / Unit 1: Fables and Folk Tales — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will revise the main grammar and vocabulary skills taught across the unit."
- **Problem:** This step's content is about a different chapter/topic, grammar and vocabulary skills, not the given chapter label, A Bottle of Dew.

### Grade 6 / English / Unit 1: Fables and Folk Tales — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will bring together the unit's themes, listening tasks, speaking practice, and writing activities."
- **Problem:** This step's content is about a different chapter/topic, unit's themes, not the given chapter label, A Bottle of Dew.

### Grade 6 / English / Unit 1: Fables and Folk Tales — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will analyse Rama to the Rescue as a problem-and-solution story."
- **Problem:** This step's content is about a different chapter/topic, Rama to the Rescue, not the given chapter label, A Bottle of Dew.

### Grade 6 / English / Unit 3: Nurturing Nature — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will interpret the four stages in What a Bird Thought."
- **Problem:** This step is about a different chapter/topic, 'What a Bird Thought', not about the neem tree.

### Grade 6 / English / Unit 3: Nurturing Nature — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will revise compound words, verb forms, personification, rhyme, adjectives, and modals."
- **Problem:** This step is about a different chapter/topic, 'What you will learn' in 'Exam-style problems', not about the neem tree.

### Grade 6 / English / Unit 3: Nurturing Nature — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will connect the reading selections with the unit's listening, speaking, writing, and exploration activities."
- **Problem:** This step is about a different chapter/topic, 'Revision and recap', not about the neem tree.

### Grade 6 / English / Unit 3: Nurturing Nature — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will read Daadi's letter as an example of knowledge shared across generations."
- **Problem:** This step is about a different chapter/topic, 'Worked examples', not about the neem tree.

### Grade 6 / English / Unit 4: Sports and Wellness — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will interpret The Winner as a poem about energetic evening play."
- **Problem:** The topic of this step is a poem about evening play, not sports and wellness.

### Grade 6 / English / Unit 4: Sports and Wellness — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will connect the unit's reading, listening, speaking, writing, and exploration activities."
- **Problem:** The topic of this step is about connecting different activities, not specifically about sports and wellness.

### Grade 6 / English / Unit 5: Culture and Tradition — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "## What you will learn
You will interpret The Kites and study how simile, alliteration, rhyme, and imagination shape the poem."
- **Problem:** This step's content is about a different chapter/topic (The Kites) than the given chapter label (Culture and Tradition).

### Grade 6 / English / Unit 5: Culture and Tradition — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "## What you will learn
You will revise sequence words, present tense, words of quantity, synonyms, antonyms, and poetic forms."
- **Problem:** This step's content is about a different chapter/topic (exam-style problems) than the given chapter label (Culture and Tradition).

### Grade 6 / English / Unit 5: Culture and Tradition — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "## What you will learn
You will connect the unit's arts, festivals, inspiring biography, national poem, and communication tasks."
- **Problem:** This step's content is about a different chapter/topic (revision and recap) than the given chapter label (Culture and Tradition).

### Grade 6 / English / Unit 5: Culture and Tradition — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "## What you will learn
You will trace Ila Sachani's journey from childhood challenge to artistic recognition and independence."
- **Problem:** This step's content is about a different chapter/topic (Ila Sachani's biography) than the given chapter label (Culture and Tradition).

### Grade 6 / Maths / Chapter 10 The Other Side of Zero — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "The historical rules agree with the number-line and movement models for positive numbers, negative numbers, and zero."
- **Problem:** This step appears to be about Brahmagupta's subtraction rules, which is a different topic from the rest of the chapter.

### Grade 6 / Maths / Chapter 2 Lines and Angles — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Accurate geometry depends on labels, reference directions, and exact degree limits."
- **Problem:** This step is discussing concepts from multiple chapters, not just Chapter 2 Lines and Angles.

### Grade 6 / Maths / Chapter 3 Number Play — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "The rule is simple: halve even numbers; for odd numbers, multiply by 3 and add 1."
- **Problem:** This step appears to be about Collatz sequences, which is a different topic from the rest of the chapter.

### Grade 6 / Maths / Chapter 4 Data Handling and Presentation — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will draw and interpret bar graphs with appropriate scales."
- **Problem:** This step's content is about bar graphs, which is a different topic than the given chapter label 'Data Handling and Presentation'.

### Grade 6 / Maths / Chapter 6 Perimeter and Area — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will connect triangle area with rectangles and review area–perimeter relationships."
- **Problem:** This step's content is about Chapter 7, not Chapter 6.

### Grade 6 / Maths / Chapter 9 Symmetry — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "The Ashoka Chakra has 24 lines and 24 angles of symmetry."
- **Problem:** This topic is not related to the chapter on symmetry, which focuses on line and rotational symmetry in 2D shapes.

### Grade 6 / Science / Chapter 5: Measurement of Length and Motion — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will describe position using a reference point and decide whether an object is in motion or at rest."
- **Problem:** This step is about position and motion, which is a different topic from measurement of length and motion.

### Grade 6 / Science / Chapter 5: Measurement of Length and Motion — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will identify linear, circular and oscillatory motion through activities and everyday examples."
- **Problem:** This step is about motion, which is a different topic from measurement of length and motion.

### Grade 6 / Science / Chapter 7: Temperature and its Measurement — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Room thermometer: A room thermometer hung on a wall gives an approximate idea of room temperature."
- **Problem:** This step is about room temperature, which is a different topic from the chapter label 'Temperature and its Measurement'.

### Grade 6 / Science / Chapter 8: A Journey through States of Water — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "how water vapour forms clouds and returns as rain, hail or snow"
- **Problem:** This topic is not covered in the SOURCE_TEXT. The chapter is about the states of water, not the water cycle.

### Grade 6 / Social Science / 10. Grassroots Democracy — Part 1: Governance — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will distinguish local, State and Central or Union government."
- **Problem:** This step is about distinguishing levels of government, but the chapter label is about grassroots democracy, which is not directly related to government levels.

### Grade 6 / Social Science / 10. Grassroots Democracy — Part 1: Governance — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will understand democracy, representation, voting and grassroots participation."
- **Problem:** This step is about democracy and representation, but the chapter label is about governance, which is a broader topic that includes but is not limited to democracy.

### Grade 6 / Social Science / 10. Grassroots Democracy — Part 1: Governance — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will understand separation of powers and checks and balances."
- **Problem:** This step is about separation of powers, but the chapter label is about governance, which is a broader topic that includes but is not limited to separation of powers.

### Grade 6 / Social Science / 2. Oceans and Continents — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "the world can be described as having four, five, six or seven continents, though seven is the most widely used count"
- **Problem:** This step is about continents, but the chapter label is 'Oceans and Continents'.

### Grade 6 / Social Science / 4. Timeline and Sources of History — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "A common mistake is to think history can be reconstructed only through texts, excavated objects, oral traditions, art, and modern scientific studies."
- **Problem:** This statement is not relevant to the current chapter, which is about timelines and sources of history, and is more relevant to the next chapter.

### Grade 6 / Social Science / 4. Timeline and Sources of History — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Early humans lived in bands or groups to help each other as they faced challenges from nature while seeking shelter and food."
- **Problem:** This statement is not relevant to the current chapter, which is about timelines and sources of history, and is more relevant to the next chapter.

### Grade 6 / Social Science / 9. Family and Community — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will examine urban community service and the many meanings of the word community."
- **Problem:** The chapter label is 'Family and Community', but this step is about urban community service, which is a different topic.

### Grade 6 / Social Science / Text Book - Part 5 - 5. India, That Is Bharat — Core explanation --- STEP: Core explanation ---
- **Type:** TOPIC_MISMATCH
- **Quote:** "## 1. What you will learn Today, we will understand the core ideas behind the name and identity of India, exploring its ancient names, how different cultures and peoples have viewed it over time, and what these names tell us about India's history and cultural diversity."
- **Problem:** This step's content is about the core ideas behind the name and identity of India, which is a different topic than the given chapter label 'India, That Is Bharat'.

### Grade 6 / Social Science / Text Book - Part 5 - 5. India, That Is Bharat — Revision and recap --- STEP: Revision and recap ---
- **Type:** TOPIC_MISMATCH
- **Quote:** "## 1. What you will learn - Understand what landforms are and their types."
- **Problem:** This step's content is about landforms, which is a different topic than the given chapter label 'India, That Is Bharat'.

### Grade 6 / Social Science / Text Book - Part 5 - 5. India, That Is Bharat — Worked examples --- STEP: Worked examples ---
- **Type:** TOPIC_MISMATCH
- **Quote:** "## 1. What you will learn - The different types of landforms: mountains, plateaus, and plains."
- **Problem:** This step's content is about landforms, which is a different topic than the given chapter label 'India, That Is Bharat'.

### Grade 7 / English / Unit 1: Learning Together — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will connect all three texts with grammar, listening and writing."
- **Problem:** This step is about connecting texts, but the source text does not mention grammar, listening, or writing as topics for this chapter.

### Grade 7 / English / Unit 3: Dreams and Discoveries — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will analyse Shaana's postcards and use evidence to show India's geographical and cultural diversity."
- **Problem:** This step's content is about a different chapter/topic than the given chapter label, 'Dreams and Discoveries'.

### Grade 7 / English / Unit 4: Travel and Adventure — Exam-style problems
- **Type:** FABRICATED_NUMBER
- **Quote:** "After 52 exhausting days, she reaches the summit on 21 May 2013."
- **Problem:** The number of days it took Arunima to climb Everest is not mentioned in the source text, making this a fabricated number.

### Grade 7 / English / Unit 4: Travel and Adventure — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Suraj explores a tunnel, the speaker dreams of any train and Arunima climbs a mountain."
- **Problem:** This step's content is about the general theme of travel and adventure, but it does not specifically relate to the chapter's focus on The Tunnel and Travel.

### Grade 7 / English / Unit 4: Travel and Adventure — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "The speaker hears and imagines trains by day and night."
- **Problem:** This step's content is about the poem 'Travel', which is not the main focus of the chapter, making it a topic mismatch.

### Grade 7 / Maths / Chapter 3: Finding Common Ground — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Certain relationships between numbers, such as one being a multiple of the other, produce predictable HCF and LCM patterns."
- **Problem:** This step is discussing a different chapter or topic, as it is not related to finding common ground.

### Grade 7 / Maths / Chapter 4: Another Peek Beyond the Point — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "A decimal divisor is changed into a counting number by multiplying both numbers in the division by the same power of ten."
- **Problem:** This statement is actually about decimal division, not multiplication, and is not relevant to the topic of decimal multiplication.

### Grade 7 / Maths / Chapter 4: Another Peek Beyond the Point — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "The Earth's revolution takes about 365.2422 days, not exactly 365."
- **Problem:** This statement is actually about the Gregorian calendar, not decimal calculations, and is not relevant to the topic of decimal multiplication and division.

### Grade 7 / Maths / Chapter 4: Another Peek Beyond the Point — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Long division does not stop when whole units cannot be shared exactly."
- **Problem:** This statement is actually about long division, not decimal multiplication or division, and is not relevant to the topic of decimal calculations.

### Grade 7 / Maths / Chapter 7: Finding the Unknown — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will interpret an unknown as a quantity whose value must be found."
- **Problem:** This chapter is about finding the unknown, but the topic mismatch is due to the chapter label being Chapter 15, not Chapter 7.

### Grade 7 / Maths / Chapter 7: Finding the Unknown — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will solve equations systematically with inverse operations."
- **Problem:** This chapter is about finding the unknown, but the topic mismatch is due to the chapter label being Chapter 15, not Chapter 7.

### Grade 7 / Maths / Chapter 7: Finding the Unknown — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will diagnose incorrect solution steps and solve equations containing brackets, negative numbers and unknowns on both sides."
- **Problem:** This chapter is about finding the unknown, but the topic mismatch is due to the chapter label being Chapter 15, not Chapter 7.

### Grade 7 / Maths / Chapter 7: Finding the Unknown — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will connect modern equation solving with the history of algebra and apply it to multi-step challenges."
- **Problem:** This chapter is about finding the unknown, but the topic mismatch is due to the chapter label being Chapter 15, not Chapter 7.

### Grade 7 / Maths / Chapter 7: Finding the Unknown — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will form equations from patterns and real-life situations."
- **Problem:** This chapter is about finding the unknown, but the topic mismatch is due to the chapter label being Chapter 15, not Chapter 7.

### Grade 7 / Science / Chapter 11: Light: Shadows and Reflections — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will explain how a pinhole camera forms an image on a screen."
- **Problem:** This step is about pinhole cameras, which is not the main topic of the chapter, which is about light, shadows, and reflections.

### Grade 7 / Science / Chapter 11: Light: Shadows and Reflections — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will apply straight-line travel and reflection to useful devices."
- **Problem:** This step is about periscopes and kaleidoscopes, which is not the main topic of the chapter, which is about light, shadows, and reflections.

### Grade 7 / Science / Chapter 11: Light: Shadows and Reflections — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will understand reflection as a change in the direction of light at a shiny surface."
- **Problem:** This step is about plane mirrors, which is not the main topic of the chapter, which is about light, shadows, and reflections.

### Grade 7 / Science / Chapter 5: Changes Around Us: Physical and Chemical — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Rocks change over very long periods. Some processes break or chemically alter them in place, while wind and water may then move the resulting particles elsewhere."
- **Problem:** This step is discussing weathering and erosion, which is a topic from a different chapter.

### Grade 7 / Science / Chapter 7: Heat Transfer in Nature — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will connect solar heat with the water cycle, infiltration and groundwater."
- **Problem:** The step discusses the water cycle and groundwater, which is not the main topic of the chapter.

### Grade 7 / Science / Chapter 8: Measurement of Time and Motion — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will classify straight-line motion as uniform or non-uniform."
- **Problem:** The SOURCE_TEXT does not discuss classifying motion as uniform or non-uniform, but it does discuss various methods of timekeeping.

### Grade 7 / Science / Chapter 9: Life Processes in Animals — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will understand why animals need digestion and trace food through the human alimentary canal."
- **Problem:** This step is about Chapter 9: Life Processes in Animals, but it discusses the human alimentary canal, which is not the topic of this chapter.

### Grade 7 / Science / Chapter 9: Life Processes in Animals — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will investigate the action of saliva through Activity 9.1."
- **Problem:** This step is about Chapter 9: Life Processes in Animals, but it discusses Activity 9.1, which is about the human alimentary canal, not the topic of this chapter.

### Grade 7 / Science / Chapter 9: Life Processes in Animals — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will distinguish breathing from respiration and model inhalation and exhalation using Activity 9.2."
- **Problem:** This step is about Chapter 9: Life Processes in Animals, but it discusses Activity 9.2, which is about the human respiratory system, not the topic of this chapter.

### Grade 7 / Science / Chapter 9: Life Processes in Animals — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will compare inhaled and exhaled air and study breathing adaptations in other animals."
- **Problem:** This step is about Chapter 9: Life Processes in Animals, but it discusses breathing adaptations in other animals, which is not the topic of this chapter.

### Grade 7 / Science / Chapter 9: Life Processes in Animals — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will compare digestion in humans, ruminants and birds."
- **Problem:** This step is about Chapter 9: Life Processes in Animals, but it discusses digestion in ruminants and birds, which is not the topic of this chapter.

### Grade 7 / Social Science / Chapter 10: The Constitution of India — An Introduction — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will define a constitution and explain why a country needs one."
- **Problem:** This step's content is about the Constitution of India, but the chapter label is 'From Barter to Money'.

### Grade 7 / Social Science / Chapter 10: The Constitution of India — An Introduction — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will trace how the Constitution was prepared."
- **Problem:** This step's content is about the Constitution of India, but the chapter label is 'From Barter to Money'.

### Grade 7 / Social Science / Chapter 10: The Constitution of India — An Introduction — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will distinguish Fundamental Rights, Fundamental Duties and Directive Principles of State Policy."
- **Problem:** This step's content is about the Constitution of India, but the chapter label is 'From Barter to Money'.

### Grade 7 / Social Science / Chapter 10: The Constitution of India — An Introduction — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will explain why the Constitution is a living document and interpret the guiding values in the Preamble."
- **Problem:** This step's content is about the Constitution of India, but the chapter label is 'From Barter to Money'.

### Grade 7 / Social Science / Chapter 10: The Constitution of India — An Introduction — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will study the three main sources that shaped the Constitution: the freedom movement, India’s civilisational heritage and useful ideas from other democratic constitutions."
- **Problem:** This step's content is about the Constitution of India, but the chapter label is 'From Barter to Money'.

### Grade 7 / Social Science / Chapter 12: Understanding Markets — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will define a market and identify its basic participants and features."
- **Problem:** This step is about understanding markets, but the provided source text is about understanding weather.

### Grade 7 / Social Science / Chapter 12: Understanding Markets — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will understand how prices respond to buyers and sellers."
- **Problem:** This step is about understanding markets, but the provided source text is about understanding weather.

### Grade 7 / Social Science / Chapter 12: Understanding Markets — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will analyse the economic and social roles of markets and the reasons for government intervention."
- **Problem:** This step is about understanding markets, but the provided source text is about understanding weather.

### Grade 7 / Social Science / Chapter 12: Understanding Markets — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will learn how consumers assess products through labels, certification marks, reputation and reviews."
- **Problem:** This step is about understanding markets, but the provided source text is about understanding weather.

### Grade 7 / Social Science / Chapter 12: Understanding Markets — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will trace how goods move from producers to consumers."
- **Problem:** This step is about understanding markets, but the provided source text is about understanding weather.

### Grade 7 / Social Science / Chapter 2: India and Her Neighbours — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will study India’s relationships with Bangladesh, Nepal, Bhutan, Myanmar and Afghanistan."
- **Problem:** This step is about a different set of countries than the chapter label 'India and Her Neighbours' suggests.

### Grade 7 / Social Science / Chapter 2: India and Her Neighbours — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will trace India’s links with Thailand, Malaysia, Singapore and Indonesia."
- **Problem:** This step is about a different set of countries than the chapter label 'India and Her Neighbours' suggests.

### Grade 7 / Social Science / Chapter 2: India and Her Neighbours — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will examine India’s western maritime links with Iran and Oman and revise the chapter’s larger patterns."
- **Problem:** This step is about a different set of countries than the chapter label 'India and Her Neighbours' suggests.

### Grade 7 / Social Science / Chapter 2: India and Her Neighbours — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will examine India’s closest maritime relationships with Sri Lanka and the Maldives."
- **Problem:** This step is about a different set of countries than the chapter label 'India and Her Neighbours' suggests.

### Grade 7 / Social Science / Chapter 2: Understanding the Weather — Worked examples
- **Type:** ARITHMETIC_ERROR
- **Quote:** "About 1013 mb is normal at the coast; below 1000 mb indicates a depression."
- **Problem:** The statement implies that 1013 mb is the normal pressure at the coast, but it does not account for the fact that pressure decreases with altitude.

### Grade 7 / Social Science / Chapter 3: Empires and Kingdoms: 6th to 10th Centuries — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will study the Tripartite Struggle and compare the Pālas, Gurjara-Pratīhāras and Rāṣhṭrakūṭas."
- **Problem:** This step is about the Tripartite Struggle, which is a different topic from the rest of the chapter that focuses on Harṣhavardhana and Xuanzang.

### Grade 7 / Social Science / Chapter 4: New Beginnings: Cities and States — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will trace urbanisation and trade beyond the Ganga plains and revise major routes and southern kingdoms."
- **Problem:** This step is about tracing urbanisation beyond the Ganga plains, which is a different topic than the rest of the chapter.

### Grade 7 / Social Science / Chapter 4: Turning Tides: 11th and 12th Centuries — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "King Bhoja, the Ghūrid advance and the destruction of major centres of learning"
- **Problem:** The topic of this step appears to be about the Ghūrids and King Bhoja, which is a different topic than the 11th and 12th centuries mentioned in the chapter label.

### Grade 7 / Social Science / Chapter 5: India, a Home to Many — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will understand the difference between internal migration and communities arriving from outside India."
- **Problem:** This step discusses Jewish and Syriac Christian experiences, which is not related to the topic of Indian agriculture.

### Grade 7 / Social Science / Chapter 5: India, a Home to Many — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will examine Parsi and Arab settlement on India’s western coast."
- **Problem:** This step discusses Parsi and Arab settlement, which is not related to the topic of Indian agriculture.

### Grade 7 / Social Science / Chapter 5: India, a Home to Many — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will examine two modern refuge stories: Polish children during the Second World War and Tibetans after 1959."
- **Problem:** This step discusses Polish and Tibetan refugees, which is not related to the topic of Indian agriculture.

### Grade 7 / Social Science / Chapter 5: India, a Home to Many — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will connect the community stories with the chapter’s values of hospitality, compassion and human unity."
- **Problem:** This step discusses community stories, which is not related to the topic of Indian agriculture.

### Grade 7 / Social Science / Chapter 5: India, a Home to Many — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will study the Siddis, Armenians and Baha’is."
- **Problem:** This step discusses Siddi, Armenian, and Baha’i communities, which is not related to the topic of Indian agriculture.

### Grade 7 / Social Science / Chapter 5: The Rise of Empires — Exam-style problems
- **Type:** INCONSISTENCY
- **Quote:** "Ashoka used inscriptions across his empire."
- **Problem:** This contradicts the SOURCE_TEXT, which states that Ashoka's edicts were placed across many regions and used a widely understood language and script.

### Grade 7 / Social Science / Chapter 5: The Rise of Empires — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Mauryan cities, art and administration were impressive, but imperial unity depended on revenue, capable rulers and cooperation across distant regions."
- **Problem:** This step is discussing the Mauryan Empire, but the chapter label is 'The Rise of Empires', which implies a broader topic of empires in general, not specifically the Mauryan Empire.

### Grade 7 / Social Science / Chapter 5: The Rise of Empires — Revision and recap
- **Type:** INCONSISTENCY
- **Quote:** "Imperial decline is not caused only by a weak ruler."
- **Problem:** This contradicts the SOURCE_TEXT, which states that empires can decline due to a variety of factors, including weak succession, rebellion, and natural or economic crises.

### Grade 7 / Social Science / Chapter 5: The Rise of Empires — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Alexander entered northwest India but did not establish lasting control across the Subcontinent."
- **Problem:** This step is discussing Alexander's campaign in northwest India, but the chapter label is 'The Rise of Empires', which implies a broader topic of empires in general, not specifically Alexander's campaign.

### Grade 7 / Social Science / Chapter 5: The Rise of Empires — Worked examples
- **Type:** INCONSISTENCY
- **Quote:** "Chandragupta later built a durable empire from Magadha."
- **Problem:** This contradicts the SOURCE_TEXT, which states that Chandragupta overthrew the Nandas and founded the Maurya Empire, but does not mention building a durable empire from Magadha.

### Grade 7 / Social Science / Chapter 7: Infrastructure: Engine of India’s Development — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Arthaśhāstra: The text assigned roles to the state, grāma and sabhās and described roads for different kinds of traffic."
- **Problem:** The topic of Arthaśhāstra is not related to the chapter's main topic of infrastructure.

### Grade 7 / Social Science / Chapter 8: Banks and the Magic of Finance — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will define shares and stocks and explain how a stock market connects investors with companies."
- **Problem:** This step's content is about stock markets, which is a different topic from the chapter label 'Banks and the Magic of Finance'.

### Grade 7 / Social Science / Chapter 9: From the Rulers to the Ruled: Types of Governments — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will compare direct and representative democracy and distinguish parliamentary from presidential systems."
- **Problem:** This step is about comparing different types of democracy, but the chapter label is 'From the Rulers to the Ruled: Types of Governments', which suggests that the chapter is about different types of governments in general, not just democracy.

### Grade 8 / English / Unit 1: Wit and Wisdom — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will study the poem A Concrete Example as a humorous portrait of Mrs Jones and her garden."
- **Problem:** This step is about a different chapter/topic, not Unit 1: Wit and Wisdom.

### Grade 8 / English / Unit 2: Values and Dispositions — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "## What you will learn
You will analyse Somebody’s Mother as a poem about kindness and empathy."
- **Problem:** This step is about analyzing a poem, but the chapter label is about values and dispositions, specifically Major Somnath Sharma and the Battle of Badgam.

### Grade 8 / English / Unit 3: Mystery and Magic — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will study The Magic Brush of Dreams as a narrative poem about kindness, power, greed, and courage."
- **Problem:** This step's content is about a different chapter/topic, 'The Magic Brush of Dreams', not the given chapter label, 'The Case of the Fifth Word'.

### Grade 8 / English / Unit 4: Environment — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will revise grammar and vocabulary drawn from all three texts."
- **Problem:** This step's content is about grammar and vocabulary, which is not relevant to the chapter's topic of the story of Rakesh and his cherry tree.

### Grade 8 / Maths / Chapter 11: Exploring Some Geometric Themes — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Fractals and projections are both geometric ways of seeing structure."
- **Problem:** This statement is not relevant to the current chapter, which is about visualizing solids, not fractals.

### Grade 8 / Maths / Chapter 7: Proportional Reasoning-1 — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "If a car travels 90 km in 150 minutes at constant speed. Find the distance in 4 hours."
- **Problem:** The step is about using the Rule of Three to solve a problem, but the SOURCE_TEXT does not mention the Rule of Three in the context of finding distance in 4 hours.

### Grade 8 / Maths / Chapter 7: Proportional Reasoning-1 — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "A proportional model is appropriate only when the relationship stays multiplicatively constant."
- **Problem:** The SOURCE_TEXT does not mention non-proportional situations, price comparisons, and sharing a whole in a ratio in the context of Chapter 7: Proportional Reasoning.

### Grade 8 / Maths / Chapter 7: Proportional Reasoning-1 — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Kesang uses 10 spoons of sugar for 6 glasses of lemonade. How many spoons are needed for 18 glasses at the same sweetness?"
- **Problem:** The SOURCE_TEXT does not mention direct-proportion problems by scale factor in the context of Chapter 7: Proportional Reasoning.

### Grade 8 / Maths / Part 1 - Exemplar: Mensuration — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "How to write numbers in standard (scientific) form and revert them back."
- **Problem:** This topic is about scientific notation, not mensuration.

### Grade 8 / Maths / Part 1 - Exemplar: Mensuration — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "The rules of exponents (product, quotient, power of a power, zero & negative exponents)."
- **Problem:** This topic is about exponent rules, not mensuration.

### Grade 8 / Maths / Part 1 - Exemplar: Mensuration — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Using these rules to convert units (km → m, tons → g, years → seconds, hectares → cm²)."
- **Problem:** This topic is about unit conversion, not mensuration.

### Grade 8 / Maths / Part 1 - Exemplar: Mensuration — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Quick strategies for adding/subtracting numbers in standard form."
- **Problem:** This topic is about arithmetic with scientific notation, not mensuration.

### Grade 8 / Maths / Part 1 - Exemplar: Mensuration — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "How to write a number in standard (scientific) form."
- **Problem:** This topic is about scientific notation, not mensuration.

### Grade 8 / Maths / Part 1 - Exemplar: Mensuration — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "The laws of exponents (product, quotient, power of a power)."
- **Problem:** This topic is about exponent rules, not mensuration.

### Grade 8 / Maths / Part 1 - Exemplar: Mensuration — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "How to apply these rules to solve typical textbook worked-example problems."
- **Problem:** This topic is about solving exponent problems, not mensuration.

### Grade 8 / Maths / Part 1 - Exemplar: Understanding Quadrilaterals and Practical Geometry — --- STEP: Core explanation ---
- **Type:** TOPIC_MISMATCH
- **Quote:** "How to identify and differentiate between parallelogram, rectangle, rhombus, square, trapezium, and kite based on their properties."
- **Problem:** This step's content is substantively about a different chapter/topic than the given chapter label.

### Grade 8 / Maths / Part 1 - Exemplar: Understanding Quadrilaterals and Practical Geometry — --- STEP: Revision and recap ---
- **Type:** TOPIC_MISMATCH
- **Quote:** "Recall the definitions of the six common quadrilaterals."
- **Problem:** This step's content is substantively about a different chapter/topic than the given chapter label.

### Grade 8 / Maths / Part 1 - Exemplar: Understanding Quadrilaterals and Practical Geometry — --- STEP: Worked examples ---
- **Type:** TOPIC_MISMATCH
- **Quote:** "How to apply the properties of different quadrilaterals (parallelogram, rectangle, rhombus, square, trapezium) to solve typical textbook problems."
- **Problem:** This step's content is substantively about a different chapter/topic than the given chapter label.

### Grade 8 / Science / Chapter 10: Light: Mirrors and Lenses — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "A convex lens is thicker in the middle and converges light."
- **Problem:** This step discusses lenses, which is a different topic than the chapter label.

### Grade 8 / Science / Chapter 11: Keeping Time with the Skies — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "Different calendars follow different sky cycles."
- **Problem:** This step is about calendars, which is a different topic from the rest of the chapter, which is about the Moon and its phases.

### Grade 8 / Science / Chapter 11: Keeping Time with the Skies — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Artificial satellites are human-made objects placed in orbit."
- **Problem:** This step is about artificial satellites, which is a different topic from the rest of the chapter, which is about the Moon and its phases.

### Grade 8 / Science / Chapter 12: How Nature Works in Harmony — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will identify habitats and separate their living and non-living components."
- **Problem:** This step is about habitats and ecosystems, but the chapter label is 'How Nature Works in Harmony', which is not about ecosystems.

### Grade 8 / Science / Chapter 12: How Nature Works in Harmony — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will analyse why every organism can matter through direct and indirect effects."
- **Problem:** This step is about ecosystem interactions and balance, but the chapter label is 'How Nature Works in Harmony', which is not about ecosystem interactions.

### Grade 8 / Science / Chapter 12: How Nature Works in Harmony — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will explain ecosystem balance as dynamic and compare competition, mutualism, commensalism, and parasitism."
- **Problem:** This step is about ecosystem interactions and balance, but the chapter label is 'How Nature Works in Harmony', which is not about ecosystem interactions.

### Grade 8 / Science / Chapter 12: How Nature Works in Harmony — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will evaluate the benefits of ecosystems and the threats caused by human activity."
- **Problem:** This step is about ecosystem benefits and threats, but the chapter label is 'How Nature Works in Harmony', which is not about ecosystem benefits and threats.

### Grade 8 / Science / Chapter 12: How Nature Works in Harmony — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will classify organisms by feeding role and build food chains, trophic levels, and food webs."
- **Problem:** This step is about food chains and trophic levels, but the chapter label is 'How Nature Works in Harmony', which is not about food chains and trophic levels.

### Grade 8 / Science / Chapter 13: Our Home: Earth, a Unique Life Sustaining Planet — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will compare asexual and sexual reproduction and explain how each supports continuity of life."
- **Problem:** This topic is not covered in the source text, which focuses on Earth's habitability and the factors that make it unique.

### Grade 8 / Science / Chapter 3: Health: The Ultimate Treasure — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Which among typhoid, asthma, diabetes and measles are non-communicable?"
- **Problem:** This question is about distinguishing between communicable and non-communicable diseases, but it's not related to the chapter topic of health and well-being.

### Grade 8 / Science / Chapter 5: Exploring Forces — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Compare magnetic, electrostatic and gravitational forces."
- **Problem:** This step is discussing forces that are not covered in the SOURCE_TEXT, which focuses on contact forces and friction.

### Grade 8 / Science / Chapter 8: Nature of Matter: Elements, Compounds, and Mixtures — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will define mixtures and distinguish uniform from non-uniform mixtures."
- **Problem:** The chapter label is Chapter 8: Nature of Matter: Elements, Compounds, and Mixtures, but this step is about mixtures, not elements, compounds, and mixtures.

### Grade 8 / Science / Chapter 8: Nature of Matter: Elements, Compounds, and Mixtures — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will explain compounds and use the iron–sulfur experiment to distinguish chemical combination from physical mixing."
- **Problem:** The chapter label is Chapter 8: Nature of Matter: Elements, Compounds, and Mixtures, but this step is about compounds, not elements, compounds, and mixtures.

### Grade 8 / Science / Chapter 8: Nature of Matter: Elements, Compounds, and Mixtures — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will connect elements, compounds and mixtures to technology, minerals and cultural materials."
- **Problem:** The chapter label is Chapter 8: Nature of Matter: Elements, Compounds, and Mixtures, but this step is about connecting elements, compounds, and mixtures to technology, minerals, and cultural materials, not just elements, compounds, and mixtures.

### Grade 8 / Science / Chapter 9: The Amazing World of Solutes, Solvents, and Solutions — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will measure mass and volume accurately and determine the density of regular and irregular solids."
- **Problem:** The topic of the step is about measuring mass and volume and determining density, but the chapter label is about solutes, solvents, and solutions.

### Grade 8 / Social Science / Chapter 14: India's Urban Landscape — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "Cities concentrate people, occupations, businesses, institutions and transport systems in relatively small areas."
- **Problem:** This step's content is about the general characteristics of cities, but the chapter label is about India's Urban Landscape.

### Grade 8 / Social Science / Chapter 14: India's Urban Landscape — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "Rapid city growth can increase opportunity while also increasing demand for land, housing, water, energy, transport and sanitation."
- **Problem:** This step's content is about the challenges of rapid urban growth, but the chapter label is about India's Urban Landscape.

### Grade 8 / Social Science / Chapter 14: India's Urban Landscape — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Urban planning tries to organise land, movement, housing, services and public spaces so that a growing city remains liveable."
- **Problem:** This step's content is about the principles of urban planning, but the chapter label is about India's Urban Landscape.

### Grade 8 / Social Science / Chapter 14: India's Urban Landscape — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "When people from many regions meet in cities, economic exchange is accompanied by cultural exchange."
- **Problem:** This step's content is about the cultural aspects of cities, but the chapter label is about India's Urban Landscape.

### Grade 8 / Social Science / Chapter 1: Natural Resources and Their Use — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will examine why natural resources are unevenly distributed and how that distribution affects human life."
- **Problem:** This step is about the uneven distribution of natural resources, which is a different topic from the rest of the chapter.

### Grade 8 / Social Science / Chapter 3: The Rise of the Marathas — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will examine Maratha administration on land and sea."
- **Problem:** This step is about Maratha administration, but the chapter label is about the Rise of the Marathas, which is more focused on their military and political strategy.

### Grade 8 / Social Science / Chapter 3: The Rise of the Marathas — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will follow the Marathas after Shivaji and explain how they became a pan-Indian power."
- **Problem:** This step is about the Marathas after Shivaji, but the chapter label is about the Rise of the Marathas, which is more focused on Shivaji's life and military strategy.

### Grade 8 / Social Science / Chapter 6: The Parliamentary System: Legislature and Executive — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Parliament and assemblies represent people only when members attend, debate seriously, examine bills, ask questions, and use time productively."
- **Problem:** This step discusses the functioning of Parliament and assemblies, but the chapter label is 'The Parliamentary System: Legislature and Executive', which implies a focus on the legislative and executive branches, not the functioning of Parliament.

### Grade 8 / Social Science / Chapter 7: Factors of Production — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Production creates benefits but can also cause pollution, unsafe work, unfair treatment, and resource depletion."
- **Problem:** This step is discussing environmental responsibility and sustainable practices, which is a topic mismatch with the chapter on Factors of Production.

### Grade 8 / Social Science / Chapter 8: World Geography: Some Glimpses — Exam-style problems: Chapter 8: World Geography: Some Glimpses
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will compare major features of Africa and South America."
- **Problem:** This step's content is about comparing Africa and South America, which is a different topic than the chapter's focus on world geography.

### Grade 9 / Advanced Mathematics / Advanced - Combinatorics — Practice questions
- **Type:** TOPIC_MISMATCH
- **Quote:** "What you will learn: In this lesson, we will practice solving various problems related to combinatorics, focusing on concepts such as permutations, combinations, and binomial coefficients."
- **Problem:** The topic of this step is not Advanced - Combinatorics, but rather a general practice of solving problems related to combinatorics.

### Grade 9 / Advanced Mathematics / Advanced - Coordinate Geometry — Practice questions
- **Type:** TOPIC_MISMATCH
- **Quote:** "To find the equation of a circle with a given center and radius, a given center and a point on the circle, and a given point on the circle and the radius."
- **Problem:** This step is about circles, not coordinate geometry.

### Grade 9 / Advanced Science / Advanced - Chemical Bonding — Practice Questions for Advanced Chemical Bonding
- **Type:** TOPIC_MISMATCH
- **Quote:** "Key concepts covered: Types of chemical bonds (ionic, covalent, metallic) Bonding in different compounds (sodium chloride, water, carbon dioxide) Polarity of molecules and its effect on bonding"
- **Problem:** The topic of the practice questions does not match the chapter label 'Advanced - Chemical Bonding' as it covers a broader range of topics including bonding in different compounds and polarity of molecules.

### Grade 9 / Advanced Science / Advanced - Engineering Life: Miracles in Biotechnology — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "Using the data in Activity 5.4 as labelled in the source - 0 h: 10, 2 h: 12, 4 h: 25, 6 h: 60, 8 h: 120, 10 h: 125, 12 h: 123, 14 h: 90 - identify the main growth phases and the period of fastest increase."
- **Problem:** This step appears to be discussing a different chapter or activity, as there is no mention of Activity 5.4 in the provided source text.

### Grade 9 / Advanced Science / Advanced - Engineering Life: Miracles in Biotechnology — Practice questions
- **Type:** TOPIC_MISMATCH
- **Quote:** "Question: A company uses genetic engineering to create a new crop that is resistant to a specific disease. The crop is made by introducing a gene from a different organism that produces a protein that kills the disease-causing agent. What is the benefit of using genetic engineering in this case?"
- **Problem:** This step appears to be discussing a different chapter or activity, as there is no mention of genetic engineering for crop disease resistance in the provided source text.

### Grade 9 / Advanced Science / Advanced - Measurement: Foundation of Science — Exam-style problems
- **Type:** ARITHMETIC_ERROR
- **Quote:** "9 km/h = 9 × 1000/3600 m/s = 5/2 m/s = 2.5 m/s."
- **Problem:** The correct calculation is 9 km/h = 9 × 1000/3600 m/s = 2.5 m/s.

### Grade 9 / Advanced Science / Advanced - Measurement: Foundation of Science — Practice questions
- **Type:** TOPIC_MISMATCH
- **Quote:** "Understanding the concept of accuracy and precision in measurement"
- **Problem:** This step's content is about a different chapter/topic than the given chapter label.

### Grade 9 / Advanced Science / Advanced - Mixtures and their Separation — Exam-Style Problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "Important Examples and Activities: Example 1: Separation of a mixture of sand and water using filtration"
- **Problem:** This example is not related to the topic of chromatography and separation of mixtures.

### Grade 9 / Advanced Science / Advanced - Newton's Laws of Motion — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will understand torque as the turning effect of force and solve problems involving force, lever arm, and angle."
- **Problem:** This step is about torque, which is not the topic of the chapter.

### Grade 9 / Advanced Science / Advanced - Newton's Laws of Motion — Practice questions
- **Type:** TOPIC_MISMATCH
- **Quote:** "Review of Newton's First Law of Motion (Inertia)"
- **Problem:** This step is about practice questions for Newton's Laws, but the chapter is about Advanced - Newton's Laws of Motion.

### Grade 9 / Advanced Science / Advanced - Structure of Atom — Practice Questions - Structure of Atom
- **Type:** TOPIC_MISMATCH
- **Quote:** "Key concepts covered: Electron configuration, atomic orbitals, energy levels, and electron shells."
- **Problem:** This step's content is about electron configuration, atomic orbitals, energy levels, and electron shells, which is a different topic than the given chapter label, 'Advanced - Structure of Atom'.

### Grade 9 / English / Chapter 1: How I Taught My Grandmother to Read — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will read Bharat Our Land as the units poem of praise."
- **Problem:** This step is about analyzing Bharat Our Land, a poem from a different chapter/unit, not about the story 'How I Taught My Grandmother to Read'.

### Grade 9 / English / Chapter 3: Winds of Change — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will examine how the unit extends its theme through The Last Leaf and Canvas of Soil."
- **Problem:** This step is about The Last Leaf and Canvas of Soil, which is a different topic than the chapter Winds of Change.

### Grade 9 / English / Chapter 5: The World of Limitless Possibilities — Exam-style problems: The World of Limitless Possibilities
- **Type:** TOPIC_MISMATCH
- **Quote:** "The poem presents a race in which one athlete falls and the other runners stop rather than continue toward individual victory."
- **Problem:** This step's content is about the poem 'Nine Gold Medals', which is not the main topic of the chapter, but rather a supporting material.

### Grade 9 / English / Chapter 5: The World of Limitless Possibilities — Revision and recap: The World of Limitless Possibilities
- **Type:** TOPIC_MISMATCH
- **Quote:** "The unit distinguishes Paralympics, Special Olympics and Olympic traditions."
- **Problem:** This step's content is about the differences between Paralympics, Special Olympics, and Olympic traditions, which is not the main topic of the chapter, but rather a supporting material.

### Grade 9 / English / Chapter 6: Twin Melodies — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "The unit notes that such instruments can be crafted from natural materials and reflect environmental and cultural connections."
- **Problem:** This content is about indigenous musical instruments, which is a topic from a different chapter.

### Grade 9 / English / Chapter 8: Follow That Dream — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "Believe in Yourself as a poem about the difficult first step into change."
- **Problem:** This step is about analyzing a poem, while the chapter is about following a dream, as discussed in the letter.

### Grade 9 / English / Grammar: Subject-Verb Concord — Core explanation: Grammar: Subject-Verb Concord
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will use the correct verb with subjects joined by `and`. You will also recognise the exception in which two nouns express one idea or entity."
- **Problem:** This step is about a different topic (verb agreement with subjects joined by `and`) than the chapter label (Subject-Verb Concord)

### Grade 9 / English / Grammar: Subject-Verb Concord — Worked examples: Grammar: Subject-Verb Concord
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will apply the nearer-subject rule with `or` and `nor`. You will choose the verb that agrees with the subject closest to it."
- **Problem:** This step is about a different topic (verb agreement with `or` and `nor`) than the chapter label (Subject-Verb Concord)

### Grade 9 / English Supplementary Reader / Chapter 5: The Happy Prince — Worked examples
- **Type:** ARITHMETIC_ERROR
- **Quote:** "Mass of gold: V = 116.7 cm^3 × 19.3 g/cm^3 ≈ 2,253 g"
- **Problem:** The calculation for the mass of gold is incorrect. The correct calculation should be V = 116.7 cm^3 × 19.3 g/cm^3 ≈ 2,253.51 g

### Grade 9 / English Supplementary Reader / Chapter 6: Weathering the Storm in Ersama — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will understand the concept of weathering, especially how natural forces break down rocks and minerals over time."
- **Problem:** This step discusses weathering in general, but the chapter is about a specific story and its context, not weathering in general.

### Grade 9 / English Supplementary Reader / Chapter 6: Weathering the Storm in Ersama — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Weathering is the process that breaks down rocks and earth materials into smaller pieces or soil."
- **Problem:** This step discusses weathering in general, but the chapter is about a specific story and its context, not weathering in general.

### Grade 9 / English Supplementary Reader / Chapter 6: Weathering the Storm in Ersama — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "In solving exam-style problems, focus on understanding what is asked, recall relevant concepts, gather data, plan your approach, and perform calculations carefully."
- **Problem:** This step discusses exam-style problems in general, but the chapter is about a specific story and its context, not exam-style problems in general.

### Grade 9 / English Supplementary Reader / Chapter 6: Weathering the Storm in Ersama — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will review and reinforce the key concepts from Chapter 6: Weathering the Storm in Ersama."
- **Problem:** This step discusses revision and recap in general, but the chapter is about a specific story and its context, not revision and recap in general.

### Grade 9 / English Supplementary Reader / Chapter 6: Weathering the Storm in Ersama — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "The coastal region of Ersama experiences heavy storms and rainfall. Over time, the rocks along the coast have started to break down into smaller pieces and form soil."
- **Problem:** This step discusses worked examples in general, but the chapter is about a specific story and its context, not worked examples in general.

### Grade 9 / Maths / Chapter 3: The World of Numbers — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will understand the concept of rational numbers, including how they are represented, their properties, and how they are placed on the number line."
- **Problem:** The topic of this step is about rational numbers, but the chapter label is 'The World of Numbers', which is about the history and development of numbers, not rational numbers specifically.

### Grade 9 / Maths / Chapter 3: The World of Numbers — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Numbers can be classified into different types based on how they can be written or expressed:"
- **Problem:** The topic of this step is about rational and irrational numbers, but the chapter label is 'The World of Numbers', which is about the history and development of numbers, not rational and irrational numbers specifically.

### Grade 9 / Maths / Chapter 3: The World of Numbers — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "How to convert rational numbers into decimal form (terminating or repeating)."
- **Problem:** The topic of this step is about rational numbers, but the chapter label is 'The World of Numbers', which is about the history and development of numbers, not rational numbers specifically.

### Grade 9 / Maths / Chapter 3: The World of Numbers — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "In this lesson, we will be covering the revision and recap of Chapter 3: The World of Numbers, focusing on key concepts such as natural numbers, integers, rational numbers, irrational numbers, and real numbers."
- **Problem:** The topic of this step is about revision and recap of Chapter 3, but the chapter label is 'The World of Numbers', which is about the history and development of numbers, not revision and recap specifically.

### Grade 9 / Maths / Chapter 3: The World of Numbers — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "Lesson: Understanding Rational Numbers and Their Placement on the Number Line"
- **Problem:** The topic of this step is about rational numbers, but the chapter label is 'The World of Numbers', which is about the history and development of numbers, not rational numbers specifically.

### Grade 9 / Maths / Chapter 4: Exploring Algebraic Identities — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "Recognize when an expression can be factored using identities."
- **Problem:** This step is about factorization, but the chapter label is about algebraic identities.

### Grade 9 / Maths / Chapter 5: I’m Up and Down, and Round and Round — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "The property that the angle subtended by a diameter at any point on the circle is 90°."
- **Problem:** This step is about cyclic quadrilaterals, not the angle in a semicircle.

### Grade 9 / Maths / Chapter 5: I’m Up and Down, and Round and Round — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "The property that the angle in a semicircle is 90°."
- **Problem:** This step is about cyclic quadrilaterals, not the angle in a semicircle.

### Grade 9 / Maths / Chapter 5: I’m Up and Down, and Round and Round — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "The property that the angle in a semicircle is 90°."
- **Problem:** This step is about cyclic quadrilaterals, not the angle in a semicircle.

### Grade 9 / Maths / Chapter 6: Measuring Space: Perimeter and Area — Concept introduction
- **Type:** TOPIC_MISMATCH
- **Quote:** "A parallelogram is a four-sided shape with opposite sides parallel."
- **Problem:** This step is about the area of a parallelogram, but the chapter label is 'Measuring Space: Perimeter and Area'.

### Grade 9 / Maths / Chapter 6: Measuring Space: Perimeter and Area — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "A parallelogram is a four-sided shape with opposite sides parallel."
- **Problem:** This step is about the area of a parallelogram, but the chapter label is 'Measuring Space: Perimeter and Area'.

### Grade 9 / Maths / Chapter 6: Measuring Space: Perimeter and Area — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "A parallelogram has opposite sides equal and parallel."
- **Problem:** This step is about the area of a parallelogram, but the chapter label is 'Measuring Space: Perimeter and Area'.

### Grade 9 / Maths / Chapter 6: Measuring Space: Perimeter and Area — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "A parallelogram is a four-sided shape with opposite sides parallel."
- **Problem:** This step is about the area of a parallelogram, but the chapter label is 'Measuring Space: Perimeter and Area'.

### Grade 9 / Maths / Chapter 6: Measuring Space: Perimeter and Area — Worked examples
- **Type:** TOPIC_MISMATCH
- **Quote:** "A parallelogram has sides opposite each other equal and parallel."
- **Problem:** This step is about the area of a parallelogram, but the chapter label is 'Measuring Space: Perimeter and Area'.

### Grade 9 / Maths / The Mathematics of Maybe: Introduction to Probability — Core explanation
- **Type:** FABRICATED_NUMBER
- **Quote:** "The number of purple cards in the deck is unknown."
- **Problem:** The example given in the source text does not mention a specific number of purple cards, but the worked example in this step assumes a deck with 6 cards.

### Grade 9 / Maths / The Mathematics of Maybe: Introduction to Probability — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Comparing experimental, theoretical, and statistical approaches to probability."
- **Problem:** This step discusses topics that are not explicitly covered in the source text, such as the Law of Large Numbers and Gambler’s Fallacy.

### Grade 9 / Maths / The Mathematics of Maybe: Introduction to Probability — Exam-style problems
- **Type:** FABRICATED_NUMBER
- **Quote:** "The number of cards in the deck is 52."
- **Problem:** The source text does not mention a specific number of cards in the deck, but the worked example in this step assumes a deck with 52 cards.

### Grade 9 / Maths / The Mathematics of Maybe: Introduction to Probability — Revision and recap
- **Type:** FABRICATED_NUMBER
- **Quote:** "The number of tyres in the recorded cases is 1000."
- **Problem:** The source text does not mention a specific number of tyres in the recorded cases, but the worked example in this step assumes 1000 tyres.

### Grade 9 / Maths / The Mathematics of Maybe: Introduction to Probability — Worked examples
- **Type:** FABRICATED_NUMBER
- **Quote:** "The number of outcomes in the sample space is 4."
- **Problem:** The source text does not mention a specific number of outcomes in the sample space, but the worked example in this step assumes 4 outcomes.

### Grade 9 / Science / Chapter 12: Patterns in Life: Diversity and Classification — Revision and recap
- **Type:** TOPIC_MISMATCH
- **Quote:** "Biodiversity refers to the variety of life on Earth, including plants, animals, fungi, bacteria, and more."
- **Problem:** This step's content is about biodiversity, but the chapter label is Patterns in Life: Diversity and Classification, which seems to focus on classification rather than biodiversity.

### Grade 9 / Science / Chapter 13: Earth as a System: Energy, Matter, and Life — Focused Lesson on How Solar Radiation Causes Uneven Heating of the Earth
- **Type:** TOPIC_MISMATCH
- **Quote:** "The Sun's energy reaches Earth in the form of electromagnetic waves."
- **Problem:** This step is about uneven heating of the Earth, which is a different topic from the chapter label 'Earth as a System: Energy, Matter, and Life'.

### Grade 9 / Science / Describing Motion Around Us — Core explanation
- **Type:** TOPIC_MISMATCH
- **Quote:** "acceleration describes a change in velocity and how motion is represented by position-time and velocity-time graphs."
- **Problem:** This step is supposed to be about describing motion around us, but it's actually about acceleration and graphs, which is a different topic.

### Grade 9 / Science / Patterns in Life: Diversity and Classification — Exam-style problems
- **Type:** TOPIC_MISMATCH
- **Quote:** "You will classify major animal groups using body organisation, symmetry, openings, segmentation, skeleton and the presence of a notochord."
- **Problem:** This step is about animal classification, which is a different topic from the chapter label 'Patterns in Life: Diversity and Classification'.

### Grade 9 / Science / Tissues in Action — Exam-Style Problems: Tissues in Action
- **Type:** TOPIC_MISMATCH
- **Quote:** "Movement needs coordinated action of nervous tissue, muscles, tendons, bones and joints."
- **Problem:** This step is about animal tissues, but the topic is about plant growth and transport.

### Grade 9 / Social Science / Chapter 1: Understanding Social Science — Revision and Recap: Understanding Social Science
- **Type:** TOPIC_MISMATCH
- **Quote:** "The chapter identifies climate change, sustainable development, social harmony, equitable resource use, and responsible technology as major areas where Social Science will remain important."
- **Problem:** This topic seems to belong to a different chapter or topic, as it is not directly related to the main ideas presented in the current chapter.

### Grade 9 / Social Science / Chapter 4: Early Humans and Beginning of Civilisation — Exam-Style Problems: Early Humans and Beginning of Civilisation
- **Type:** TOPIC_MISMATCH
- **Quote:** "Egypt and China developed in different river valleys and created their own systems of rule, writing, craft production, social hierarchy, and belief."
- **Problem:** The step is discussing the social hierarchy and daily life of people in the Egyptian civilisation and China, but the chapter label is 'Early Humans and Beginning of Civilisation', which does not match the topic of the step.

### Grade 9 / Social Science / Chapter 4: Early Humans and Beginning of Civilisation — Worked Examples: Early Humans and Beginning of Civilisation
- **Type:** TOPIC_MISMATCH
- **Quote:** "The chapter presents civilisation as the result of many connected changes rather than a single invention."
- **Problem:** The step is discussing the rise of the Sindhu-Sarasvati and Mesopotamian civilisations, but the chapter label is 'Early Humans and Beginning of Civilisation', which does not match the topic of the step.

### Grade 9 / Social Science / Chapter 6: Democracy — Worked Examples: Democracy
- **Type:** TOPIC_MISMATCH
- **Quote:** "Direct democracy: Citizens directly participate in most decision-making processes."
- **Problem:** This step is about direct democracy, but the chapter label is about democracy in general.

### Grade 9 / Social Science / Chapter 8: Building Blocks in Economics: The Problem of Choice — Exam-Style Problems: Building Blocks in Economics: The Problem of Choice
- **Type:** TOPIC_MISMATCH
- **Quote:** "A purely planned system can restrict private competition through extensive government ownership, permits, licences, and production targets, which may weaken incentives for quality improvement and innovation."
- **Problem:** This step is about planned, market, and mixed economies, which is a different topic from the rest of the chapter.

---

## Medium severity issues

- **Grade 10 / English / Chapter 5: Glimpses of India — Core explanation** [UNSUPPORTED_CLAIM]: "Bread is woven into marriages, engagements, feasts, Christmas, and village routine." — SOURCE_TEXT does not explicitly state that bread is woven into Christmas, although it does mention the importance of bread in Goan life.
- **Grade 10 / Social Science / Chapter 3: Money and Credit — Core explanation** [UNSUPPORTED_CLAIM]: "Banks charge a higher interest rate on loans than the interest they pay on deposits; the difference is a main source of income." — The source text does not mention banks making a profit from the difference between lending and deposit rates.
- **Grade 11 / Chemistry / Chapter 5: Thermodynamics — Core explanation** [UNSUPPORTED_CLAIM]: "Internal-energy change equals energy transferred as heat and work." — This statement is a simplification and not entirely accurate. The first law of thermodynamics is ΔU = q + w, but it does not directly state that internal-energy change equals energy transferred as heat and work.
- **Grade 11 / Chemistry / Chapter 5: Thermodynamics — Exam-style problems** [UNSUPPORTED_CLAIM]: "Enthalpy is a state function, so reaction routes can be combined algebraically." — This statement is a simplification and not entirely accurate. Enthalpy is a state function, but it does not directly state that reaction routes can be combined algebraically.
- **Grade 11 / Chemistry / Chapter 5: Thermodynamics — Revision and recap** [UNSUPPORTED_CLAIM]: "At constant temperature and pressure, Gibbs energy combines enthalpy and entropy into a direction criterion." — This statement is a simplification and not entirely accurate. Gibbs energy combines enthalpy and entropy into a direction criterion, but it does not directly state that it is at constant temperature and pressure.
- **Grade 11 / Economics / Chapter 2: Indian Economy 1950–1990 — Concept introduction: Indian Economy 1950–1990** [UNSUPPORTED_CLAIM]: "At Independence, India needed to rebuild agriculture, expand industry and raise living standards." — This statement is not supported by the source text, which does not mention the need to rebuild agriculture or raise living standards.
- **Grade 11 / Economics / Chapter 2: Indian Economy 1950–1990 — Core explanation: Indian Economy 1950–1990** [UNSUPPORTED_CLAIM]: "At Independence, many cultivators lacked ownership and security." — This statement is not supported by the source text, which does not mention the lack of ownership and security among cultivators.
- **Grade 11 / Economics / Chapter 2: Indian Economy 1950–1990 — Worked examples: Indian Economy 1950–1990** [UNSUPPORTED_CLAIM]: "The Green Revolution used high-yielding variety seeds with irrigation, fertilisers and other inputs." — This statement is not supported by the source text, which does not mention the Green Revolution or its specific inputs.
- **Grade 12 / Business Studies / Chapter 5: Organising — Revision and recap** [INCONSISTENCY]: "Decentralisation is an extension of delegation throughout lower levels of the organisation." — This statement contradicts the source text, which states that decentralisation is an organisation-wide policy and degree of authority dispersal, while delegation is individual and essential.
- **Grade 12 / English / Chapter 17: The Enemy — Exam-style problems: The Enemy** [INCONSISTENCY]: "The General promises private killers, not from justice or mercy, but because he needs Sadao’s surgical skill and wants the difficulty removed secretly." — This statement contradicts the previous statement that the General's motive is self-absorption, not patriotism or national loyalty.
- **Grade 12 / English / Chapter 17: The Enemy — Worked examples: The Enemy** [INCONSISTENCY]: "Sadao says he ought to give Tom to the police but does not know what he will do." — This statement contradicts the previous statement that Sadao has already decided to help Tom and has given him a boat to escape.
- **Grade 12 / Geography / Chapter 6: Tertiary and Quaternary Activities — Core explanation: Tertiary and Quaternary Activities** [UNSUPPORTED_CLAIM]: "Trade is the buying and selling of items produced elsewhere for profit and takes place through trading centres." — This claim is not supported by the source text, which does not mention trading centres.
- **Grade 12 / Geography / Chapter 6: Tertiary and Quaternary Activities — Exam-style problems: Tertiary and Quaternary Activities** [UNSUPPORTED_CLAIM]: "Knowledge services can be delivered from distant locations because they are not tightly tied to raw materials or local markets." — This claim is not supported by the source text, which does not mention knowledge services or their delivery from distant locations.
- **Grade 12 / Geography / Chapter 6: Tertiary and Quaternary Activities — Revision and recap: Tertiary and Quaternary Activities** [UNSUPPORTED_CLAIM]: "Outsourcing shifts work to outside agencies for efficiency and cost savings." — This claim is not supported by the source text, which does not mention outsourcing or its purpose.
- **Grade 12 / Political Science / Chapter 2: Contemporary Centres of Power — Core explanation: Contemporary Centres of Power** [UNSUPPORTED_CLAIM]: "ASEAN created an informal and cooperative regional framework that protected sovereignty while promoting economic growth, social progress, cultural development, peace and stability." — This description of ASEAN does not appear in the SOURCE_TEXT, and its accuracy is unclear.
- **Grade 5 / English / 10. Glass Bangles — Exam-style problems** [TOPIC_MISMATCH]: "Question: Why must the laddu steps be reordered?" — The step is about making besan laddus, not glass bangles.
- **Grade 6 / Hindi / 1. मातृभूमि — Concept introduction** [UNSUPPORTED_CLAIM]: "कवि भारत को केवल रहने की जगह नहीं मानता, बल्कि माँ के समान प्रिय भूमि के रूप में देखता है।" — यह दावा समर्थन के बिना किया गया है और पाठ में भारत को माँ के समान प्रिय भूमि के रूप में देखते हुए कोई स्पष्टीकरण नहीं मिलता है।
- **Grade 6 / Hindi / 1. मातृभूमि — Core explanation** [UNSUPPORTED_CLAIM]: "कविता में भारत केवल सुंदर प्रकृति वाला देश नहीं है। यह धर्मभूमि, कर्मभूमि, उन महान व्यक्तित्वों की जन्मभूमि भी है जिनसे मर्यादा, ज्ञान, गीता, दया और प्रकाश का भाव जुड़ा है।" — यह दावा समर्थन के बिना किया गया है और पाठ में भारत को धर्मभूमि, कर्मभूमि, और महान व्यक्तित्वों की जन्मभूमि के रूप में देखते हुए कोई स्पष्टीकरण नहीं मिलता है।
- **Grade 6 / Hindi / 1. मातृभूमि — Exam-style problems** [UNSUPPORTED_CLAIM]: "‘दया’ और ‘दिया’ में केवल एक मात्रा का अंतर है, पर ‘दया’ करुणा और ‘दिया’ प्रकाश का अर्थ देता है।" — यह दावा समर्थन के बिना किया गया है और पाठ में ‘दया’ और ‘दिया’ के अर्थों को स्पष्ट करने के लिए कोई स्पष्टीकरण नहीं मिलता है।
- **Grade 6 / Hindi / 1. मातृभूमि — Revision and recap** [UNSUPPORTED_CLAIM]: "‘पुष्प की अभिलाषा’ में पुष्प कहाँ अर्पित होना चाहता है? उस पथ पर जहाँ मातृभूमि पर शीश चढ़ाने के लिए अनेक वीर जाते हैं।" — यह दावा समर्थन के बिना किया गया है और पाठ में पुष्प की अभिलाषा के वास्तविक अर्थ को स्पष्ट करने के लिए कोई स्पष्टीकरण नहीं मिलता है।
- **Grade 6 / Hindi / 1. मातृभूमि — Worked examples** [UNSUPPORTED_CLAIM]: "‘लहर’ से नदियों के बहते जल की गति और ‘छहर’ से सुंदरता के चारों ओर फैलने का अर्थ मिलता है।" — यह दावा समर्थन के बिना किया गया है और पाठ में ‘लहर’ और ‘छहर’ के अर्थों को स्पष्ट करने के लिए कोई स्पष्टीकरण नहीं मिलता है।
- **Grade 6 / Social Science / 9. Family and Community — Worked examples** [INCONSISTENCY]: "Shalini's family uses its resources to include Chittappa, Chitti and Chinni, who are facing financial difficulty." — This statement contradicts the source text, which states that Shalini's family bought clothes for everyone, including Chittappa, Chitti, and Chinni, but Shalini did not get the silk dress she wanted.
- **Grade 7 / Maths / Chapter 2: Operations with Integers — Core explanation** [UNSUPPORTED_CLAIM]: "A negative multiplier is interpreted through removing equal groups, using zero pairs when the required tokens are not initially present." — This claim is not supported by the source text, which uses the token model to explain that a negative multiplier means placing negative tokens into the bag.
- **Grade 7 / Maths / Chapter 2: Operations with Integers — Core explanation** [UNSUPPORTED_CLAIM]: "Two negative factors give a positive product." — This claim is not supported by the source text, which explains that two negative factors give a negative product.
- **Grade 7 / Social Science / Chapter 3: Empires and Kingdoms: 6th to 10th Centuries — Exam-style problems** [UNSUPPORTED_CLAIM]: "Villages, landholders, traders, women, poets, saints and scholars also transformed Indian society." — The chapter does not provide enough information to support the claim that women, poets, saints, and scholars transformed Indian society.
- **Grade 8 / Hindi / Chapter 9: आदमी का अनुपात — Core explanation** [UNSUPPORTED_CLAIM]: "विराट ब्रह्मांड के सामने छोटा मनुष्य स्वयं को दूसरों का स्वामी मानता है।" — यह दावा कविता में नहीं कहा गया है, बल्कि कविता में यह कहा गया है कि मनुष्य दूसरों को स्वामी मानता है।
- **Grade 8 / Science / Chapter 8: Nature of Matter: Elements, Compounds, and Mixtures — Core explanation** [UNSUPPORTED_CLAIM]: "Air contains several gases, including nitrogen, oxygen, argon and carbon dioxide." — The source text does not mention the specific gases present in air.
- **Grade 8 / Science / Chapter 8: Nature of Matter: Elements, Compounds, and Mixtures — Worked examples** [UNSUPPORTED_CLAIM]: "The chapter lists quartz among minerals made of more than one element." — The source text does not mention quartz as an example of a mineral made of more than one element.
- **Grade 9 / Science / Patterns in Life: Diversity and Classification — Revision and recap** [INCONSISTENCY]: "The hierarchy is Kingdom → Phylum → Class → Order → Family → Genus → Species." — This statement contradicts the statement in the previous step that the hierarchy is Kingdom → Phylum → Class → Order → Family → Genus → Species, but with the genus starting with a capital letter and the species with a lower-case letter.

---

## Chapters that errored (could not audit)

- Grade 6 / Social Science / Text Book - Part 10 - 10. Grassroots Democracy — Part 1: Governance: unparseable LLM response: Expecting ',' delimiter: line 25 column 2 (char 1314)
- Grade 8 / Maths / Chapter 1: A Square and A Cube: unparseable LLM response: Expecting ',' delimiter: line 30 column 2 (char 759)
- Grade 8 / Maths / Part 1 - Exemplar: Playing with Numbers: unparseable LLM response: Invalid \escape: line 21 column 36 (char 445)
- Grade 10 / English / Supplementary Reader - Chapter 3: The Midnight Visitor: unparseable LLM response: Expecting ',' delimiter: line 31 column 2 (char 1251)
- Grade 11 / Geography / Chapter 7: Composition and Structure of Atmosphere: unparseable LLM response: Expecting ',' delimiter: line 15 column 5 (char 589)
- Grade 11 / Mathematics / Chapter 2: Relations and Functions: unparseable LLM response: Expecting ',' delimiter: line 20 column 42 (char 792)
- Grade 11 / Mathematics / Principle of Mathematical Induction: unparseable LLM response: Invalid \escape: line 17 column 116 (char 567)
- Grade 11 / Physics / Chapter 13: Oscillations: unparseable LLM response: Invalid \escape: line 32 column 63 (char 1184)
- Grade 12 / Hindi / Chapter 15: Shram Vibhajan Aur Jati Pratha: unparseable LLM response: Expecting ',' delimiter: line 7 column 5 (char 316)
- Grade 12 / Hindi / Chapter 8: Rubaiyan: unparseable LLM response: Expecting ',' delimiter: line 29 column 2 (char 1409)
- Grade 12 / Hindi / Chapter 9: Chhota Mera Khet: unparseable LLM response: Expecting ',' delimiter: line 7 column 5 (char 331)

---
_Low-severity issues are omitted from this report for readability — see the CSV for the full list._
_Generated by audit_lesson_content_accuracy.py_