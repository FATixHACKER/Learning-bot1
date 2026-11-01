"""Built-in question bank for the quiz feature.

Each entry: (question, [wrong answers...], correct answer)
The bot shuffles the options so the right answer is never always in the same spot.
"""

SUBJECTS = [
    "Math", "Physics", "Chemistry", "Biology",
    "History", "English", "Programming", "General",
]

QUESTION_BANK: dict[str, list[dict]] = {
    "Math": [
        {"q": "What is 15% of 200?", "options": ["30", "45", "60", "25"], "answer": "30"},
        {"q": "What is the derivative of x^2?", "options": ["2x", "x", "2", "x^3"], "answer": "2x"},
        {"q": "How many sides does a hexagon have?", "options": ["6", "5", "8", "7"], "answer": "6"},
        {"q": "What is the square root of 144?", "options": ["12", "14", "16", "10"], "answer": "12"},
        {"q": "What is 2/3 + 1/3?", "options": ["1", "3/5", "2/6", "1/6"], "answer": "1"},
        {"q": "What is the value of pi to 2 decimal places?", "options": ["3.14", "3.16", "3.12", "3.18"], "answer": "3.14"},
        {"q": "Solve for x: 2x + 6 = 14", "options": ["4", "5", "3", "6"], "answer": "4"},
        {"q": "What is the area of a circle with radius 3? (use pi = 3.14)",
         "options": ["28.26", "31.4", "9.42", "18.84"], "answer": "28.26"},
    ],
    "Physics": [
        {"q": "What is the SI unit of force?", "options": ["Newton", "Joule", "Watt", "Pascal"], "answer": "Newton"},
        {"q": "What is the speed of light in a vacuum?",
         "options": ["300,000 km/s", "150,000 km/s", "3,000 km/s", "3,000,000 km/s"], "answer": "300,000 km/s"},
        {"q": "Who formulated E = mc^2?", "options": ["Einstein", "Newton", "Bohr", "Curie"], "answer": "Einstein"},
        {"q": "What does F = ma stand for?", "options": ["Force = mass x acceleration", "Energy = mass x acceleration",
                                                      "Force = momentum x acceleration", "Frequency = mass x acceleration"],
         "answer": "Force = mass x acceleration"},
        {"q": "What is the unit of electrical resistance?", "options": ["Ohm", "Volt", "Ampere", "Watt"], "answer": "Ohm"},
        {"q": "What planet is known as the Red Planet?", "options": ["Mars", "Venus", "Jupiter", "Mercury"], "answer": "Mars"},
    ],
    "Chemistry": [
        {"q": "How many protons does carbon have?", "options": ["6", "8", "12", "4"], "answer": "6"},
        {"q": "What is the chemical symbol for gold?", "options": ["Au", "Ag", "Go", "Gd"], "answer": "Au"},
        {"q": "What is the pH of pure water at 25°C?", "options": ["7", "0", "14", "5"], "answer": "7"},
        {"q": "What state of matter is room-temperature water?", "options": ["Liquid", "Solid", "Gas", "Plasma"], "answer": "Liquid"},
        {"q": "How many elements are in a water molecule?", "options": ["2", "3", "4", "1"], "answer": "2"},
        {"q": "What is the most abundant gas in Earth's atmosphere?", "options": ["Nitrogen", "Oxygen", "CO2", "Argon"], "answer": "Nitrogen"},
    ],
    "Biology": [
        {"q": "What organ pumps blood around the body?", "options": ["Heart", "Liver", "Lung", "Kidney"], "answer": "Heart"},
        {"q": "What is the powerhouse of the cell?", "options": ["Mitochondrion", "Nucleus", "Ribosome", "Vacuole"], "answer": "Mitochondrion"},
        {"q": "How many chromosomes does a human cell normally have?", "options": ["46", "23", "48", "44"], "answer": "46"},
        {"q": "What process do plants use to make food from sunlight?", "options": ["Photosynthesis", "Respiration", "Transpiration", "Osmosis"], "answer": "Photosynthesis"},
        {"q": "Which blood type is the universal donor?", "options": ["O negative", "AB positive", "A positive", "B negative"], "answer": "O negative"},
    ],
    "History": [
        {"q": "In which year did World War II end?", "options": ["1945", "1939", "1944", "1950"], "answer": "1945"},
        {"q": "Who was the first President of the United States?",
         "options": ["George Washington", "Thomas Jefferson", "John Adams", "Benjamin Franklin"], "answer": "George Washington"},
        {"q": "The Berlin Wall fell in which year?", "options": ["1989", "1991", "1985", "1979"], "answer": "1989"},
        {"q": "Which empire was ruled by Julius Caesar's successor Augustus?", "options": ["Roman", "Greek", "Ottoman", "Persian"], "answer": "Roman"},
        {"q": "The Magna Carta was signed in which country?", "options": ["England", "France", "Italy", "Spain"], "answer": "England"},
    ],
    "English": [
        {"q": "Which word is a synonym for 'happy'?", "options": ["Joyful", "Angry", "Quiet", "Heavy"], "answer": "Joyful"},
        {"q": "What is the plural of 'child'?", "options": ["Children", "Childs", "Childrens", "Childes"], "answer": "Children"},
        {"q": "Which is a verb: 'quickly'?", "options": ["No, it's an adverb", "Yes", "Only in past tense", "Only with 'be'"], "answer": "No, it's an adverb"},
        {"q": "What is the opposite of 'ancient'?", "options": ["Modern", "Old", "Historic", "Antique"], "answer": "Modern"},
        {"q": "Which punctuation ends a question?", "options": ["Question mark", "Full stop", "Comma", "Semicolon"], "answer": "Question mark"},
    ],
    "Programming": [
        {"q": "What does CPU stand for?", "options": ["Central Processing Unit", "Computer Personal Unit",
                                                    "Central Program Unit", "Control Processing Utility"],
         "answer": "Central Processing Unit"},
        {"q": "In Python, which keyword defines a function?", "options": ["def", "fun", "function", "define"], "answer": "def"},
        {"q": "What does RAM stand for?", "options": ["Random Access Memory", "Rapid Access Memory",
                                                    "Read Access Module", "Runtime Application Memory"],
         "answer": "Random Access Memory"},
        {"q": "Which of these is a database language?", "options": ["SQL", "Python", "HTML", "CSS"], "answer": "SQL"},
        {"q": "What does 'HTML' stand for?", "options": ["HyperText Markup Language", "High Transfer Machine Language",
                                                       "Hyperlink Text Making Language", "Home Tool Markup Language"],
         "answer": "HyperText Markup Language"},
        {"q": "Which data structure works on a First-In-First-Out basis?", "options": ["Queue", "Stack", "Tree", "Graph"], "answer": "Queue"},
    ],
    "General": [
        {"q": "How many continents are there?", "options": ["7", "5", "6", "8"], "answer": "7"},
        {"q": "What is the largest ocean on Earth?", "options": ["Pacific", "Atlantic", "Indian", "Arctic"], "answer": "Pacific"},
        {"q": "How many minutes are in a full day?", "options": ["1440", "360", "720", "60"], "answer": "1440"},
        {"q": "What gas do plants absorb from the air?", "options": ["Carbon dioxide", "Oxygen", "Nitrogen", "Helium"], "answer": "Carbon dioxide"},
        {"q": "What is the hardest natural substance?", "options": ["Diamond", "Quartz", "Steel", "Granite"], "answer": "Diamond"},
    ],
}
