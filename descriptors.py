# descriptors.py
# Kim Marshall Teacher Evaluation Rubric – Strand Descriptors (A1–F9)

DESCRIPTORS = {
    # Domain A: Planning and Preparation for Learning
    "A1 Expertise": {
        "HE": "Deep content knowledge; models intellectual curiosity; uses rich repertoire of instructional strategies.",
        "E": "Solid content knowledge; explanations are clear; engages students with appropriate strategies.",
        "IN": "Limited content knowledge; explanations sometimes unclear; repertoire of strategies is narrow.",
        "DNMS": "Insufficient content knowledge; confuses students; lacks strategies to support learning."
    },
    "A2 Goals": {
        "HE": "Clear, rigorous, measurable goals aligned to standards; inspire students to aim high.",
        "E": "Clear goals aligned to standards; goals guide teaching and learning effectively.",
        "IN": "Goals are vague or not fully aligned; students lack clarity on what they are learning.",
        "DNMS": "Goals are missing, unclear, or unrelated to standards."
    },
    "A3 Units": {
        "HE": "Units are well-sequenced, rigorous, and aligned to long-term standards; anticipate student misconceptions.",
        "E": "Units are coherent, appropriately sequenced, and standards-aligned.",
        "IN": "Units show limited planning or weak alignment to standards.",
        "DNMS": "Units are unplanned, fragmented, or not aligned to standards."
    },
    "A4 Assessments": {
        "HE": "Designs assessments upfront; checks for understanding continuously; aligns with goals.",
        "E": "Uses assessments aligned to goals and checks for student understanding regularly.",
        "IN": "Assessments are irregular or weakly aligned; limited formative checks.",
        "DNMS": "Rarely or never assesses; assessments are misaligned or absent."
    },
    "A5 Anticipation": {
        "HE": "Anticipates student misconceptions and proactively plans scaffolds and supports.",
        "E": "Plans for common difficulties and provides supports as needed.",
        "IN": "Limited anticipation of learning obstacles; support is reactive.",
        "DNMS": "Does not anticipate difficulties; students are left to struggle."
    },
    "A6 Lessons": {
        "HE": "Lessons are consistently rigorous, well-paced, and tightly aligned to goals.",
        "E": "Lessons are clear, purposeful, and aligned to goals.",
        "IN": "Lessons sometimes lack focus, pacing, or rigor.",
        "DNMS": "Lessons are disorganized, unfocused, or off-task."
    },
    "A7 Materials": {
        "HE": "Materials are rich, varied, culturally responsive, and enhance learning.",
        "E": "Materials support learning effectively and are appropriate.",
        "IN": "Materials are limited, outdated, or not always supportive of goals.",
        "DNMS": "Materials are missing, irrelevant, or detract from learning."
    },
    "A8 Differentiation": {
        "HE": "Consistently differentiates instruction, tasks, and supports to meet all learners’ needs.",
        "E": "Differentiates instruction for most learners; adapts when needed.",
        "IN": "Occasional differentiation; often uses one-size-fits-all instruction.",
        "DNMS": "No differentiation; ignores varied learning needs."
    },
    "A9 Environment": {
        "HE": "Classroom culture fosters intellectual risk-taking, curiosity, and high expectations.",
        "E": "Classroom culture is positive and conducive to learning.",
        "IN": "Classroom culture is inconsistent or low-expectation.",
        "DNMS": "Classroom culture is negative, unsafe, or non-conducive to learning."
    },

    # Domain B: Classroom Management
    "B1 Expectations": {
        "HE": "Clear, consistent, and high expectations for behavior and routines; students internalize them.",
        "E": "Expectations are clear and usually followed by students.",
        "IN": "Expectations are inconsistently enforced or unclear.",
        "DNMS": "Expectations are absent or ignored."
    },
    "B2 Relationships": {
        "HE": "Strong, respectful, and supportive teacher-student relationships; fosters peer respect.",
        "E": "Positive teacher-student relationships and classroom rapport.",
        "IN": "Relationships are inconsistent; some students feel unsupported.",
        "DNMS": "Relationships are poor; classroom feels disrespectful."
    },
    "B3 Social Emotional": {
        "HE": "Explicitly supports SEL; students self-regulate, empathize, and collaborate effectively.",
        "E": "Supports SEL and student well-being.",
        "IN": "Limited SEL support; inconsistently addresses needs.",
        "DNMS": "No attention to SEL; dismisses student well-being."
    },
    "B4 Routines": {
        "HE": "Routines are efficient, student-led, and maximize learning time.",
        "E": "Routines are clear and generally effective.",
        "IN": "Routines are inconsistently followed; some learning time lost.",
        "DNMS": "No routines or chaotic routines; much time wasted."
    },
    "B5 Responsibility": {
        "HE": "Students take ownership of routines, learning, and classroom responsibilities.",
        "E": "Students share responsibility for routines and learning.",
        "IN": "Students occasionally take responsibility but inconsistently.",
        "DNMS": "Students avoid responsibility; teacher does all management."
    },
    "B6 Repertoire": {
        "HE": "Uses varied proactive strategies to maintain a positive learning climate.",
        "E": "Uses effective strategies to maintain order and engagement.",
        "IN": "Relies on limited or reactive strategies; effectiveness varies.",
        "DNMS": "Does not use strategies; class is often off-task."
    },
    "B7 Prevention": {
        "HE": "Proactively prevents misbehavior through engaging teaching and culture.",
        "E": "Usually prevents misbehavior; responds appropriately when it occurs.",
        "IN": "Misbehavior prevention is inconsistent or weak.",
        "DNMS": "Does little to prevent misbehavior; frequent disruptions."
    },
    "B8 Incentives": {
        "HE": "Motivates students through intrinsic incentives, pride, and ownership.",
        "E": "Uses incentives appropriately to encourage positive behavior.",
        "IN": "Over-reliance on external incentives or inconsistent use.",
        "DNMS": "Incentives are absent, unfair, or ineffective."
    },

    # Domain C: Delivery of Instruction
    "C1 Expectations": {
        "HE": "Challenges all students with high cognitive demand; fosters deep learning.",
        "E": "Sets appropriate expectations that promote learning.",
        "IN": "Expectations are too low or uneven.",
        "DNMS": "Expectations are absent or inappropriate."
    },
    "C2 Mindset": {
        "HE": "Promotes growth mindset; students persist and embrace challenges.",
        "E": "Encourages effort and perseverance.",
        "IN": "Mindset messages are inconsistent or superficial.",
        "DNMS": "Conveys fixed mindset; discourages effort."
    },
    "C3 Framing": {
        "HE": "Frames learning with clear purpose, real-world connections, and student buy-in.",
        "E": "Frames lessons with purpose and relevance.",
        "IN": "Framing is limited or unclear.",
        "DNMS": "No framing; students don’t know why they’re learning."
    },
    "C4 Connections": {
        "HE": "Makes strong interdisciplinary and real-life connections.",
        "E": "Makes some relevant connections to prior knowledge or life.",
        "IN": "Connections are occasional or weak.",
        "DNMS": "No meaningful connections are made."
    },
    "C5 Clarity": {
        "HE": "Explanations and instructions are crystal-clear and scaffolded for all learners.",
        "E": "Explanations are generally clear and support learning.",
        "IN": "Explanations are sometimes unclear or confusing.",
        "DNMS": "Explanations are muddled or absent."
    },
    "C6 Repertoire": {
        "HE": "Wide repertoire of instructional strategies; maximizes engagement and learning.",
        "E": "Uses appropriate instructional strategies effectively.",
        "IN": "Limited repertoire; relies heavily on one method.",
        "DNMS": "Fails to use strategies; students disengaged."
    },
    "C7 Engagement": {
        "HE": "Students are highly engaged, lead discussions, and collaborate deeply.",
        "E": "Most students are engaged and participate actively.",
        "IN": "Engagement is uneven; some students are passive.",
        "DNMS": "Students are disengaged; off-task."
    },
    "C8 Differentiation": {
        "HE": "Instruction is consistently differentiated to meet varied needs.",
        "E": "Instruction is sometimes differentiated; most needs met.",
        "IN": "Minimal differentiation; many needs unmet.",
        "DNMS": "No differentiation at all."
    },
    "C9 Nimbleness": {
        "HE": "Adapts fluidly to student needs and classroom dynamics.",
        "E": "Adjusts instruction when needed.",
        "IN": "Adjustments are slow or partial.",
        "DNMS": "Does not adapt; instruction continues regardless of needs."
    },

    # Domain D: Monitoring, Assessment, and Follow-Up
    "D1 Criteria": {
        "HE": "Clear success criteria shared with students; they can self-assess effectively.",
        "E": "Success criteria are shared and generally clear.",
        "IN": "Criteria are vague or not consistently shared.",
        "DNMS": "Criteria are absent."
    },
    "D2 Diagnosis": {
        "HE": "Continuously diagnoses student understanding through checks and probes.",
        "E": "Uses formative assessments to gauge learning.",
        "IN": "Occasional or weak diagnosis of understanding.",
        "DNMS": "No diagnosis; teaching continues without checking."
    },
    "D3 Goals": {
        "HE": "Students set, monitor, and reflect on ambitious learning goals.",
        "E": "Teacher sets goals and helps students track progress.",
        "IN": "Goals are rarely tracked or monitored.",
        "DNMS": "No learning goals in place."
    },
    "D4 Feedback": {
        "HE": "Feedback is timely, specific, actionable, and drives improvement.",
        "E": "Feedback is helpful and usually timely.",
        "IN": "Feedback is vague, late, or inconsistent.",
        "DNMS": "Feedback is absent or unhelpful."
    },
    "D5 Recognition": {
        "HE": "Recognizes academic growth authentically; celebrates learning.",
        "E": "Recognizes student effort and achievement.",
        "IN": "Recognition is infrequent or generic.",
        "DNMS": "Recognition is absent or unfair."
    },
    "D6 Analysis": {
        "HE": "Regularly analyzes assessment data to adjust instruction.",
        "E": "Uses assessment data to guide some adjustments.",
        "IN": "Rarely analyzes or responds to data.",
        "DNMS": "Does not use assessment data."
    },
    "D7 Tenacity": {
        "HE": "Pursues every student’s success relentlessly; follows up until mastery.",
        "E": "Supports struggling students until progress is made.",
        "IN": "Follow-up is limited or inconsistent.",
        "DNMS": "Little or no follow-up with students."
    },
    "D8 Support": {
        "HE": "Provides intensive supports; mobilizes resources for struggling learners.",
        "E": "Provides extra help as needed.",
        "IN": "Provides limited or delayed support.",
        "DNMS": "Provides no extra help."
    },
    "D9 Reflection": {
        "HE": "Reflects deeply and continuously; improves practice based on evidence.",
        "E": "Reflects regularly and makes some improvements.",
        "IN": "Reflection is superficial or rare.",
        "DNMS": "Does not reflect or improve practice."
    },

    # Domain E: Family and Community Outreach
    "E1 Respect": {
        "HE": "Highly respectful, culturally responsive, and builds strong family partnerships.",
        "E": "Respectful and positive with families.",
        "IN": "Respect is inconsistent; communication limited.",
        "DNMS": "Disrespectful or dismissive of families."
    },
    "E2 Belief": {
        "HE": "Communicates belief in every student’s ability to succeed; families are inspired.",
        "E": "Communicates belief in students’ abilities.",
        "IN": "Messages of belief are inconsistent or weak.",
        "DNMS": "Conveys low expectations to families."
    },
    "E3 Expectations": {
        "HE": "Sets and communicates high expectations for students with families.",
        "E": "Shares expectations clearly with families.",
        "IN": "Expectations are vague or inconsistent.",
        "DNMS": "Does not share expectations."
    },
    "E4 Communication": {
        "HE": "Ongoing, two-way, proactive communication with families.",
        "E": "Regular, clear communication with families.",
        "IN": "Communication is sporadic or generic.",
        "DNMS": "Rarely or never communicates with families."
    },
    "E5 Involving": {
        "HE": "Families actively involved in learning; genuine partnership built.",
        "E": "Families are involved appropriately.",
        "IN": "Limited involvement of families.",
        "DNMS": "Families are excluded or ignored."
    },
    "E6 Responsiveness": {
        "HE": "Responds to family concerns with urgency and empathy.",
        "E": "Responds to family concerns in a timely way.",
        "IN": "Responses are delayed or superficial.",
        "DNMS": "Ignores family concerns."
    },
    "E7 Reporting": {
        "HE": "Reports are clear, comprehensive, and actionable for families.",
        "E": "Reports are clear and regular.",
        "IN": "Reports are incomplete or infrequent.",
        "DNMS": "Reports are missing or confusing."
    },
    "E8 Outreach": {
        "HE": "Actively reaches out to hard-to-reach families and builds trust.",
        "E": "Reaches out to families as needed.",
        "IN": "Outreach is minimal or inconsistent.",
        "DNMS": "No outreach efforts made."
    },
    "E9 Resources": {
        "HE": "Connects families with resources and supports proactively.",
        "E": "Provides resources when requested.",
        "IN": "Provides limited resources.",
        "DNMS": "Provides no resources."
    },

    # Domain F: Professional Responsibility
    "F1 Language": {
        "HE": "Consistently uses professional, respectful, and inclusive language.",
        "E": "Generally uses respectful and professional language.",
        "IN": "Language is occasionally unprofessional or careless.",
        "DNMS": "Language is unprofessional or disrespectful."
    },
    "F2 Reliability": {
        "HE": "Always reliable; meets deadlines and commitments with excellence.",
        "E": "Usually reliable and meets commitments.",
        "IN": "Sometimes unreliable; misses deadlines.",
        "DNMS": "Frequently unreliable; fails to meet commitments."
    },
    "F3 Professionalism": {
        "HE": "Exemplary professionalism; a role model for colleagues.",
        "E": "Professional and respectful in conduct.",
        "IN": "Professionalism is inconsistent.",
        "DNMS": "Unprofessional conduct undermines school culture."
    },
    "F4 Judgement": {
        "HE": "Consistently exercises sound judgment; decisions benefit all students.",
        "E": "Usually exercises good judgment.",
        "IN": "Judgment is sometimes questionable.",
        "DNMS": "Frequently exercises poor judgment."
    },
    "F5 Teamwork": {
        "HE": "Collaborates effectively; strengthens teams; shares leadership.",
        "E": "Works well with colleagues and contributes.",
        "IN": "Teamwork is inconsistent or limited.",
        "DNMS": "Rarely collaborates; isolates from colleagues."
    },
    "F6 Leadership": {
        "HE": "Takes initiative; mentors colleagues; contributes beyond classroom.",
        "E": "Takes some initiative and leadership roles.",
        "IN": "Occasional leadership, but minimal impact.",
        "DNMS": "No leadership or initiative."
    },
    "F7 Openness": {
        "HE": "Highly open to feedback; actively seeks improvement.",
        "E": "Open to feedback and makes adjustments.",
        "IN": "Sometimes resistant to feedback.",
        "DNMS": "Rejects feedback and resists improvement."
    },
    "F8 Collaboration": {
        "HE": "Deeply collaborative; builds strong professional culture.",
        "E": "Collaborates with colleagues productively.",
        "IN": "Collaboration is occasional or weak.",
        "DNMS": "Does not collaborate with colleagues."
    },
    "F9 Growth": {
        "HE": "Engages in continuous professional growth; shares learning widely.",
        "E": "Pursues professional development and applies it.",
        "IN": "Engages in minimal professional development.",
        "DNMS": "Shows no interest in growth."
    },
}
