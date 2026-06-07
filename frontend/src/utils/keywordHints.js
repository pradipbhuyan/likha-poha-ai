const KEYWORD_HINTS = {
  atom: "The smallest unit of an element that can take part in a chemical reaction.",
  atoms: "The smallest units of matter that keep the properties of an element.",
  molecule: "Two or more atoms chemically joined together.",
  molecules: "Groups of atoms chemically joined together.",
  matter: "Anything that has mass and takes up space.",
  element: "A pure substance made of only one kind of atom.",
  elements: "Pure substances made of only one kind of atom each.",
  compound: "A substance made when two or more different elements chemically combine.",
  compounds: "Substances made when different elements chemically combine in fixed ratios.",
  "chemical reaction": "A change where old substances form new substances.",
  "chemical reactions": "Changes where old substances form new substances.",
  "law of conservation of mass":
    "Mass is neither created nor destroyed during a chemical reaction.",
  "law of definite proportions":
    "A compound always contains the same elements in the same fixed ratio by mass.",
  "dalton's atomic theory":
    "The idea that matter is made of tiny particles called atoms.",
  "atomic theory": "A scientific model explaining that matter is made of atoms.",
  solute: "The substance that dissolves in a solvent.",
  solvent: "The liquid or substance that dissolves a solute.",
  solution: "A uniform mixture formed when a solute dissolves in a solvent.",
  pressure: "Force acting on a unit area.",
  density: "Mass packed into a given volume.",
  force: "A push or pull that can change motion or shape.",
  motion: "A change in position with time.",
  velocity: "Speed in a particular direction.",
  acceleration: "The rate at which velocity changes.",
  energy: "The ability to do work or cause change.",
  gravitation: "The force of attraction between objects that have mass.",
  sound: "Energy produced by vibrations and heard by our ears.",
  osmosis:
    "Movement of water through a selectively permeable membrane from dilute to concentrated solution.",
  photosynthesis:
    "The process by which green plants make food using sunlight, carbon dioxide, and water.",
  chlorophyll: "The green pigment in leaves that captures sunlight for photosynthesis.",
  stomata: "Tiny pores on leaves that help gases enter and leave.",
  xylem: "Plant tissue that carries water and minerals upward from roots.",
  phloem: "Plant tissue that carries food made in leaves to other parts.",
  cell: "The basic structural and functional unit of life.",
  tissue: "A group of similar cells working together.",
  ecosystem: "Living organisms and their physical environment interacting together.",
  "rational number": "A number that can be written as p/q, where q is not zero.",
  "rational numbers": "Numbers that can be written as p/q, where q is not zero.",
  "irrational number": "A number that cannot be written exactly as p/q.",
  "irrational numbers": "Numbers that cannot be written exactly as p/q.",
  numerator: "The top number in a fraction; it tells how many parts are taken.",
  denominator: "The bottom number in a fraction; it tells the total equal parts.",
  fraction: "A number showing part of a whole or a ratio of two numbers.",
  proportion: "A statement that two ratios are equal.",
  proportional: "Changing in a constant ratio.",
  equation: "A mathematical statement showing two expressions are equal.",
  variable: "A letter or symbol that stands for an unknown or changing value.",
  polynomial: "An expression made of variables, constants, and whole-number powers.",
  "coordinate geometry":
    "Geometry that uses x and y coordinates to locate points and study shapes.",
  triangle: "A polygon with three sides and three angles.",
  quadrilateral: "A polygon with four sides.",
  circle: "A set of points at the same distance from a fixed centre.",
  "surface area": "The total area covering the outside of a 3D object.",
  volume: "The amount of space occupied by a 3D object.",
  statistics: "The study of collecting, organising, and interpreting data.",
  probability: "A measure of how likely an event is to happen.",
  noun: "A word that names a person, place, thing, or idea.",
  pronoun: "A word used instead of a noun.",
  adjective: "A word that describes a noun or pronoun.",
  adverb: "A word that describes a verb, adjective, or another adverb.",
  verb: "A word that shows an action, state, or occurrence.",
  tense: "The form of a verb that shows time, such as past, present, or future.",
  preposition: "A word that shows relation, such as place, time, or direction.",
  conjunction: "A word that joins words, phrases, or clauses.",
  synonym: "A word with a similar meaning.",
  antonym: "A word with an opposite meaning.",
  comprehension: "Understanding a passage and answering based on its meaning.",
  democracy: "A system where people choose their representatives or leaders.",
  constitution: "A set of basic rules and principles for governing a country.",
  development: "Improvement in people's lives, income, health, education, and opportunities.",
  resources: "Things available in nature or society that people can use.",
  economy: "The system of producing, earning, spending, and exchanging goods and services.",
  credit: "Money borrowed with a promise to repay later.",
  globalisation:
    "Growing connection between countries through trade, technology, and movement of people.",
  globalization:
    "Growing connection between countries through trade, technology, and movement of people.",
  agriculture: "Farming, including growing crops and raising animals.",
  manufacturing: "Making goods from raw materials using labour, machines, or tools.",
  climate: "The usual weather pattern of a place over a long time.",
  monsoon: "Seasonal winds that bring heavy rainfall in many parts of India.",
};

const GENERIC_LABELS = new Set([
  "activity",
  "activity from the textbook",
  "answer",
  "common mistake",
  "example",
  "important",
  "key point",
  "mistake",
  "note",
  "question",
  "quick check question",
  "remember",
  "solution",
  "step",
  "summary",
  "what you will learn",
  "why it's wrong",
  "why its wrong",
  "worked example",
]);

function flattenText(value) {
  if (value === null || value === undefined) {
    return "";
  }

  if (typeof value === "string" || typeof value === "number") {
    return String(value);
  }

  if (Array.isArray(value)) {
    return value.map(flattenText).join("");
  }

  if (value?.props?.children) {
    return flattenText(value.props.children);
  }

  return "";
}

function cleanLookupKey(text) {
  return text
    .toLowerCase()
    .replace(/[`*_]/g, "")
    .replace(/[()[\]{}]/g, "")
    .replace(/\s+/g, " ")
    .replace(/[.,:;!?]+$/g, "")
    .trim();
}

export function normalizeKeywordText(children) {
  return flattenText(children).replace(/\s+/g, " ").trim();
}

export function getKeywordHint(children) {
  const displayText = normalizeKeywordText(children);
  const lookupKey = cleanLookupKey(displayText);

  if (!displayText || !lookupKey) {
    return "";
  }

  if (GENERIC_LABELS.has(lookupKey)) {
    return "";
  }

  const candidates = [
    lookupKey,
    lookupKey.endsWith("s") ? lookupKey.slice(0, -1) : lookupKey,
  ];

  for (const candidate of candidates) {
    if (KEYWORD_HINTS[candidate]) {
      return `${displayText}: ${KEYWORD_HINTS[candidate]}`;
    }
  }

  const phraseMatch = Object.keys(KEYWORD_HINTS).find(
    (term) =>
      (lookupKey.length > 4 && term.includes(lookupKey)) ||
      (term.length > 3 && lookupKey.includes(term))
  );

  if (phraseMatch) {
    return `${displayText}: ${KEYWORD_HINTS[phraseMatch]}`;
  }

  return "";
}
