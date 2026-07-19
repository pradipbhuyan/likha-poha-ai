/**
 * Exemplar Research — NCERT Exemplar topic deep-dive screen.
 * Mirrors the web ExemplarResearchPage.jsx.
 * Shows curated NCERT Exemplar topic cards with AI explanations
 * and practice MCQs via POST /api/doubt/answer.
 * Premium feature — free users see an upgrade prompt.
 */
import { useEffect, useRef, useState } from "react";
import {
  View, Text, ScrollView, StyleSheet,
  TouchableOpacity, ActivityIndicator, Linking, TextInput,
} from "react-native";
import { Feather } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import Markdown from "react-native-markdown-display";
import { authFetch } from "../../lib/authFetch";
import { BRAND_COLOR } from "../../constants";

type TopicCard = { topic: string; chapter: string; difficulty: string; hint: string };

// ── Curated topic cards — mirrors frontend/src/pages/ExemplarResearchPage.jsx ──
// `chapter` is the canonical NCERT chapter name used at RAG ingestion time
// (see backend/scripts/download_ncert_exemplar*.py) — sent as "Exemplar: {chapter}"
// so /api/doubt/answer's textbook-context retrieval hits the ingested Exemplar PDFs.
const TOPIC_CARDS: Record<string, Record<string, TopicCard[]>> = {
  "Grade 8": {
    Maths: [
      { topic: "Rational Numbers on Number Line", chapter: "Rational Numbers", difficulty: "Tricky", hint: "Plotting fractions and decimals between integers" },
      { topic: "Squares and Square Roots", chapter: "Square-Square Root and Cube-Cube Root", difficulty: "Hard", hint: "Long division method and patterns in perfect squares" },
      { topic: "Cubes and Cube Roots", chapter: "Square-Square Root and Cube-Cube Root", difficulty: "Hard", hint: "Prime factorisation and cube root tricks" },
      { topic: "Algebraic Expressions and Identities", chapter: "Algebraic Expressions and Identities", difficulty: "Tricky", hint: "(a+b)2 = a2+2ab+b2 and other key identities" },
      { topic: "Mensuration — Area and Volume", chapter: "Mensuration", difficulty: "Hard", hint: "Surface area of cubes, cuboids, and cylinders" },
      { topic: "Linear Equations in One Variable", chapter: "Linear Equation in One Variable", difficulty: "Tricky", hint: "Word problems and transposing terms" },
      { topic: "Comparing Quantities — Percentage, Profit Loss", chapter: "Comparing Quantities", difficulty: "Tricky", hint: "Simple interest and compound interest" },
      { topic: "Data Handling — Bar Graphs and Probability", chapter: "Data Handling", difficulty: "Medium", hint: "Reading data and computing simple probability" },
      { topic: "Direct and Inverse Proportions", chapter: "Direct and Inverse Proportions", difficulty: "Tricky", hint: "Identify direct vs inverse, cross-multiplication shortcuts" },
      { topic: "Understanding Quadrilaterals", chapter: "Understanding Quadrilaterals and Practical Geometry", difficulty: "Hard", hint: "Angle sum, properties of parallelogram, rhombus, trapezium" },
      { topic: "Playing with Numbers — Divisibility", chapter: "Playing with Numbers", difficulty: "Medium", hint: "Divisibility rules for 2,3,4,5,6,9,11 and puzzles" },
      { topic: "Introduction to Graphs — Line and Bar", chapter: "Introduction to Graphs", difficulty: "Medium", hint: "Reading coordinates, plotting and interpreting bar/line graphs" },
    ],
    Science: [
      { topic: "Microorganisms — Friend and Foe", chapter: "Microorganisms: Friend and Foe", difficulty: "Tricky", hint: "Bacteria, fungi, viruses and their roles" },
      { topic: "Cell — Structure and Functions", chapter: "Cell - Structure and Functions", difficulty: "Hard", hint: "Animal vs plant cell, organelles and their functions" },
      { topic: "Conservation of Plants and Animals", chapter: "Conservation of Plants and Animals", difficulty: "Medium", hint: "Biodiversity, endangered species, deforestation" },
      { topic: "Combustion and Flame", chapter: "Combustion and Flame", difficulty: "Tricky", hint: "Types of combustion, fire triangle, fire extinguishers" },
      { topic: "Force and Pressure", chapter: "Force and Pressure", difficulty: "Hard", hint: "Contact vs non-contact forces, atmospheric pressure" },
      { topic: "Sound — Nature and Propagation", chapter: "Sound", difficulty: "Tricky", hint: "Frequency, amplitude, audible range and vibrations" },
      { topic: "Light — Reflection and Refraction", chapter: "Light", difficulty: "Hard", hint: "Laws of reflection, types of mirrors and lenses" },
      { topic: "Pollution of Air and Water", chapter: "Pollution of Air and Water", difficulty: "Medium", hint: "Causes, effects and measures to control pollution" },
      { topic: "Reproduction in Animals", chapter: "Reproduction in Animals", difficulty: "Medium", hint: "Sexual vs asexual reproduction, human reproduction basics" },
      { topic: "Metals and Non-Metals", chapter: "Materials: Metals and Non-Metals", difficulty: "Tricky", hint: "Physical and chemical properties, uses, reactions with acids" },
      { topic: "Friction — Types and Effects", chapter: "Friction", difficulty: "Tricky", hint: "Static, sliding, rolling friction; ways to increase/decrease" },
      { topic: "Stars and the Solar System", chapter: "Stars and the Solar System", difficulty: "Medium", hint: "Planets, stars, constellations, moon phases, satellites" },
    ],
  },
  "Grade 9": {
    Maths: [
      { topic: "Number System — Irrational Numbers", chapter: "Number Systems", difficulty: "Hard", hint: "Representation on number line, rationalising denominators" },
      { topic: "Polynomials — Remainder & Factor Theorem", chapter: "Polynomials", difficulty: "Hard", hint: "p(x) at x=a, factorising using the factor theorem" },
      { topic: "Coordinate Geometry — Plotting Points", chapter: "Coordinate Geometry", difficulty: "Medium", hint: "Quadrants, x and y axis, plotting (x,y)" },
      { topic: "Lines and Angles — Parallel Lines", chapter: "Lines and Angles", difficulty: "Tricky", hint: "Alternate angles, co-interior angles, transversal proofs" },
      { topic: "Triangles — Congruence Rules", chapter: "Triangles", difficulty: "Hard", hint: "SSS, SAS, ASA, AAS, RHS congruence conditions" },
      { topic: "Surface Area and Volume of Solids", chapter: "Surface Areas and Volumes", difficulty: "Hard", hint: "Cone, cylinder, sphere — curved surface vs total surface" },
      { topic: "Statistics — Mean, Median, Mode", chapter: "Statistics", difficulty: "Tricky", hint: "Grouped data, frequency tables, bar vs histogram" },
      { topic: "Quadrilaterals — Properties and Proofs", chapter: "Quadrilaterals", difficulty: "Hard", hint: "Mid-point theorem, properties of parallelogram" },
      { topic: "Circles — Arcs, Chords and Angles", chapter: "Circles", difficulty: "Hard", hint: "Equal chords, angles subtended at centre vs circumference" },
      { topic: "Heron's Formula — Area of Triangle", chapter: "Heron's Formula", difficulty: "Tricky", hint: "s = (a+b+c)/2, A = sqrt(s(s-a)(s-b)(s-c))" },
      { topic: "Probability — Basic Concepts", chapter: "Probability", difficulty: "Medium", hint: "Sample space, events, P(E) = n(E)/n(S)" },
      { topic: "Constructions — Bisectors and Triangles", chapter: "Constructions", difficulty: "Medium", hint: "Perpendicular bisector, angle bisector, triangle constructions" },
    ],
    Science: [
      { topic: "Matter in Our Surroundings — States of Matter", chapter: "Matter in Our Surroundings", difficulty: "Tricky", hint: "Evaporation, sublimation, latent heat and inter-conversion" },
      { topic: "Structure of the Atom — Models", chapter: "Structure of the Atom", difficulty: "Hard", hint: "Thomson, Rutherford, Bohr models — electrons and nucleus" },
      { topic: "Force and Laws of Motion", chapter: "Force and Laws of Motion", difficulty: "Hard", hint: "Newton's 3 laws, inertia, F=ma, action-reaction pairs" },
      { topic: "Gravitation — Universal Law", chapter: "Gravitation", difficulty: "Hard", hint: "g = GM/R2, weight vs mass, free fall" },
      { topic: "Work, Energy and Power", chapter: "Work and Energy", difficulty: "Tricky", hint: "W=Fs*cos(theta), KE = 1/2*mv2, conservation of energy" },
      { topic: "Sound — Wave Properties", chapter: "Sound", difficulty: "Tricky", hint: "Speed, frequency, wavelength, echo, ultrasound" },
      { topic: "Tissues — Plant and Animal", chapter: "Tissues", difficulty: "Hard", hint: "Meristematic vs permanent, types of animal tissues" },
      { topic: "Natural Resources — Atmosphere and Water", chapter: "Natural Resources", difficulty: "Medium", hint: "Nitrogen cycle, water cycle, air composition" },
      { topic: "Motion — Distance, Speed, Velocity", chapter: "Motion", difficulty: "Hard", hint: "Scalar vs vector, v=u+at, s=ut+1/2at2" },
      { topic: "Diversity in Living Organisms", chapter: "Diversity in Living Organisms", difficulty: "Tricky", hint: "Kingdoms, classification criteria, Whittaker's 5-kingdom system" },
      { topic: "Why Do We Fall Ill — Health and Disease", chapter: "Why Do We Fall Ill", difficulty: "Medium", hint: "Infectious vs non-infectious, immune system, prevention" },
      { topic: "Improvement in Food Resources", chapter: "Improvement in Food Resources", difficulty: "Medium", hint: "Crop production, manures, irrigation, animal husbandry" },
    ],
  },
  "Grade 10": {
    Maths: [
      { topic: "Real Numbers — Euclid's Algorithm & HCF", chapter: "Real Numbers", difficulty: "Hard", hint: "Division algorithm, HCF via Euclid, prime factorisation" },
      { topic: "Polynomials — Relationship of Zeroes", chapter: "Polynomials", difficulty: "Hard", hint: "Sum and product of zeroes, quadratic and cubic polynomials" },
      { topic: "Quadratic Equations — Discriminant", chapter: "Quadratic Equations", difficulty: "Hard", hint: "D>0 two roots, D=0 equal roots, D<0 no real roots" },
      { topic: "Arithmetic Progressions — nth Term", chapter: "Arithmetic Progressions", difficulty: "Tricky", hint: "a_n = a+(n-1)d, sum Sn = n/2(2a+(n-1)d)" },
      { topic: "Triangles — Similarity and Pythagoras", chapter: "Triangles", difficulty: "Hard", hint: "BPT theorem, AA, SAS, SSS similarity criteria" },
      { topic: "Introduction to Trigonometry", chapter: "Introduction to Trigonometry and Its Applications", difficulty: "Hard", hint: "sin2+cos2=1, ratios in right triangles, values at 30/45/60°" },
      { topic: "Areas Related to Circles", chapter: "Areas Related to Circles", difficulty: "Tricky", hint: "Sector area, arc length, segment area — mixed problems" },
      { topic: "Surface Areas and Volumes — Combined Solids", chapter: "Surface Areas and Volumes", difficulty: "Hard", hint: "Cone on cylinder, hemisphere on sphere" },
      { topic: "Statistics — Grouped Data, Median, Mode", chapter: "Statistics", difficulty: "Tricky", hint: "Median from cumulative frequency, mode from frequency table" },
      { topic: "Probability — Playing Cards and Dice", chapter: "Probability", difficulty: "Medium", hint: "Deck of 52 cards, two-dice problems, compound events" },
      { topic: "Coordinate Geometry — Section Formula", chapter: "Coordinate Geometry", difficulty: "Tricky", hint: "Distance, section, midpoint formulas and area of triangle" },
      { topic: "Constructions — Tangents and Similar Triangles", chapter: "Constructions", difficulty: "Tricky", hint: "Tangent from external point, triangle construction with ratio" },
    ],
    Science: [
      { topic: "Chemical Reactions and Equations", chapter: "Chemical Reactions and Equations", difficulty: "Hard", hint: "Balancing equations, types of reactions — combination, displacement" },
      { topic: "Acids, Bases and Salts", chapter: "Acids, Bases and Salts", difficulty: "Tricky", hint: "pH scale, neutralisation, common salts and their uses" },
      { topic: "Life Processes — Nutrition and Respiration", chapter: "Life Processes", difficulty: "Hard", hint: "Autotrophic vs heterotrophic, aerobic vs anaerobic respiration" },
      { topic: "Electricity — Ohm's Law and Circuits", chapter: "Electricity", difficulty: "Hard", hint: "V=IR, series and parallel circuits, power P=VI" },
      { topic: "Magnetic Effects of Current", chapter: "Magnetic Effects of Electric Current", difficulty: "Hard", hint: "Right-hand thumb rule, motor effect, electromagnetic induction" },
      { topic: "Refraction of Light — Lenses", chapter: "Light - Reflection and Refraction", difficulty: "Hard", hint: "Lens formula 1/v-1/u=1/f, magnification, power of lens" },
      { topic: "Heredity and Evolution — Mendel's Laws", chapter: "Heredity and Evolution", difficulty: "Tricky", hint: "Dominant/recessive traits, Punnett square, natural selection" },
      { topic: "Carbon and Its Compounds", chapter: "Carbon and Its Compounds", difficulty: "Hard", hint: "Covalent bonding, functional groups, homologous series, reactions" },
      { topic: "Control and Coordination — Nervous System", chapter: "Control and Coordination", difficulty: "Tricky", hint: "Reflex arc, brain parts, hormones and their functions" },
      { topic: "Light — Reflection and Spherical Mirrors", chapter: "Light - Reflection and Refraction", difficulty: "Hard", hint: "Mirror formula, sign convention, ray diagrams for concave/convex" },
      { topic: "Our Environment — Food Chains", chapter: "Our Environment", difficulty: "Medium", hint: "Trophic levels, biomagnification, ozone depletion" },
      { topic: "Sources of Energy — Conventional and New", chapter: "Sources of Energy", difficulty: "Medium", hint: "Fossil fuels, solar, wind, nuclear — advantages and limitations" },
    ],
  },
  "Grade 11": {
    Physics: [
      { topic: "Units & Measurement — Dimensional Analysis", chapter: "Units and Measurements", difficulty: "Hard", hint: "Derive formulae using dimensions, check homogeneity, SI prefixes" },
      { topic: "Motion in a Straight Line — Kinematics", chapter: "Motion in a Straight Line", difficulty: "Hard", hint: "v=u+at, s=ut+1/2at2, v2=u2+2as, sign convention for direction" },
      { topic: "Motion in a Plane — Projectile Motion", chapter: "Motion in a Plane", difficulty: "Hard", hint: "Horizontal range R=u2sin2theta/g, max height, time of flight" },
      { topic: "Laws of Motion — Newton & Friction", chapter: "Laws of Motion", difficulty: "Hard", hint: "F=ma, pseudo forces, static vs kinetic friction, inclined planes" },
      { topic: "Work, Energy and Power — Conservation", chapter: "Work, Energy and Power", difficulty: "Hard", hint: "W=Fs*cos(theta), KE=1/2mv2, elastic vs inelastic collisions" },
      { topic: "Rotational Motion — Moment of Inertia", chapter: "System of Particles and Rotational Motion", difficulty: "Hard", hint: "tau=I*alpha, angular momentum L=I*omega, theorems of MI" },
      { topic: "Gravitation — Kepler's Laws", chapter: "Gravitation", difficulty: "Hard", hint: "T2 proportional to r3, escape velocity, orbital velocity, gravitational PE" },
      { topic: "Mechanical Properties of Solids", chapter: "Mechanical Properties of Solids", difficulty: "Tricky", hint: "Stress, strain, Young's modulus, Hooke's law, elastic limit" },
      { topic: "Fluid Mechanics — Bernoulli's Theorem", chapter: "Mechanical Properties of Fluids", difficulty: "Hard", hint: "P+1/2*rho*v2+rho*g*h=constant, surface tension, viscosity" },
      { topic: "Thermal Properties — Expansion & Calorimetry", chapter: "Thermal Properties of Matter", difficulty: "Tricky", hint: "Linear, area, volume expansion; specific heat; Newton's law of cooling" },
      { topic: "Thermodynamics — Laws and Processes", chapter: "Thermodynamics", difficulty: "Hard", hint: "1st law dU=Q-W; isothermal/adiabatic/isobaric processes; Carnot efficiency" },
      { topic: "Kinetic Theory of Gases — RMS Speed", chapter: "Kinetic Theory", difficulty: "Hard", hint: "PV=nRT, vrms=sqrt(3RT/M), degrees of freedom, equipartition theorem" },
    ],
    Chemistry: [
      { topic: "Some Basic Concepts — Mole and Stoichiometry", chapter: "Some Basic Concepts of Chemistry", difficulty: "Hard", hint: "Mole concept, limiting reagent, % yield, empirical vs molecular formula" },
      { topic: "Structure of Atom — Quantum Numbers", chapter: "Structure of Atom", difficulty: "Hard", hint: "n,l,m,s quantum numbers, Pauli exclusion, Hund's rule, aufbau principle" },
      { topic: "Periodic Table — Periodic Trends", chapter: "Classification of Elements and Periodicity in Properties", difficulty: "Tricky", hint: "IE, EA, electronegativity, atomic radius trends across periods and groups" },
      { topic: "Chemical Bonding — VSEPR and Hybridisation", chapter: "Chemical Bonding and Molecular Structure", difficulty: "Hard", hint: "sp, sp2, sp3 hybridisation; VSEPR shapes; bond angle vs lone pairs" },
      { topic: "States of Matter — Kinetic Theory of Gases", chapter: "States of Matter", difficulty: "Tricky", hint: "Ideal gas equation, van der Waals, real vs ideal gas deviations" },
      { topic: "Thermodynamics — Hess's Law", chapter: "Thermodynamics", difficulty: "Hard", hint: "dH, dS, dG = dH-TdS; spontaneity; Born-Haber cycle" },
      { topic: "Equilibrium — Kp, Kc and Le Chatelier", chapter: "Equilibrium", difficulty: "Hard", hint: "Kc=[products]/[reactants], Kp=Kc(RT)^Dn, buffer solutions, pH" },
      { topic: "Redox Reactions — Oxidation Number", chapter: "Redox Reactions", difficulty: "Tricky", hint: "Assign oxidation number, balance by ON method, electrode notation" },
      { topic: "s-Block Elements — Anomalous Properties", chapter: "The s-Block Elements", difficulty: "Tricky", hint: "Li and Be diagonal relationship, flame test, Na2O2 reactions" },
      { topic: "p-Block Elements — Group 13 & 14", chapter: "The p-Block Elements", difficulty: "Hard", hint: "Boron chemistry, inert pair effect, allotropy of carbon, silicones" },
      { topic: "Organic Chemistry — IUPAC Nomenclature", chapter: "Organic Chemistry: Some Basic Principles and Techniques", difficulty: "Hard", hint: "Priority rules, E/Z isomerism, functional group nomenclature order" },
      { topic: "Hydrocarbons — Alkanes, Alkenes, Alkynes", chapter: "Hydrocarbons", difficulty: "Hard", hint: "FR substitution in alkanes, electrophilic addition, Markovnikov's rule" },
    ],
    Biology: [
      { topic: "Living World — Classification Criteria", chapter: "The Living World", difficulty: "Tricky", hint: "Biodiversity, nomenclature, ICBN rules, binomial nomenclature" },
      { topic: "Biological Classification — 5 Kingdoms", chapter: "Biological Classification", difficulty: "Hard", hint: "Monera, Protista, Fungi, Plantae, Animalia — Whittaker's criteria" },
      { topic: "Plant Kingdom — Alternation of Generations", chapter: "Plant Kingdom", difficulty: "Hard", hint: "Algae, bryophytes, pteridophytes, gymnosperms, angiosperms" },
      { topic: "Animal Kingdom — Basis of Classification", chapter: "Animal Kingdom", difficulty: "Hard", hint: "Levels of organization, symmetry, coelom, segmentation, notochord" },
      { topic: "Cell — Structure and Ultra-structure", chapter: "Cell: The Unit of Life", difficulty: "Hard", hint: "Prokaryote vs eukaryote, cell organelles, membrane structure (fluid mosaic)" },
      { topic: "Cell Division — Mitosis and Meiosis", chapter: "Cell Cycle and Cell Division", difficulty: "Hard", hint: "Phases of mitosis/meiosis, crossing over, significance" },
      { topic: "Transport in Plants — Osmosis and Imbibition", chapter: "Transport in Plants", difficulty: "Tricky", hint: "Water potential, plasmolysis, transpiration pull, ascent of sap" },
      { topic: "Mineral Nutrition — Essential Elements", chapter: "Mineral Nutrition", difficulty: "Tricky", hint: "Macro vs micro nutrients, deficiency symptoms, nitrogen fixation" },
      { topic: "Photosynthesis — Light and Dark Reactions", chapter: "Photosynthesis in Higher Plants", difficulty: "Hard", hint: "PS I & II, Calvin cycle, C3 vs C4 plants, photorespiration" },
      { topic: "Respiration — Glycolysis and Krebs Cycle", chapter: "Respiration in Plants", difficulty: "Hard", hint: "ATP yield, ETS, oxidative phosphorylation, RQ of fats vs carbs" },
      { topic: "Plant Growth and Development — Phytohormones", chapter: "Plant Growth and Development", difficulty: "Tricky", hint: "Auxin, gibberellin, cytokinin, abscisic acid, ethylene functions" },
      { topic: "Morphology of Flowering Plants", chapter: "Morphology of Flowering Plants", difficulty: "Tricky", hint: "Root, stem, leaf modifications; inflorescence types; floral formula" },
    ],
    Maths: [
      { topic: "Sets — Operations and De Morgan's Laws", chapter: "Sets", difficulty: "Tricky", hint: "Union, intersection, complement; De Morgan's; Venn diagram problems" },
      { topic: "Relations and Functions — Types", chapter: "Relations and Functions", difficulty: "Hard", hint: "One-one, onto, bijective; inverse function; composition of functions" },
      { topic: "Trigonometric Functions — Identities", chapter: "Trigonometric Functions", difficulty: "Hard", hint: "Addition, double angle, half angle formulae; solving equations in [0,2pi]" },
      { topic: "Principle of Mathematical Induction", chapter: "Principle of Mathematical Induction", difficulty: "Tricky", hint: "P(1) true, assume P(k), prove P(k+1) — divisibility and sum problems" },
      { topic: "Complex Numbers — Modulus-Argument Form", chapter: "Complex Numbers and Quadratic Equations", difficulty: "Hard", hint: "z=a+ib, |z|, arg(z), cube roots of unity, De Moivre's theorem" },
      { topic: "Linear Inequalities — Graphical Method", chapter: "Linear Inequalities", difficulty: "Tricky", hint: "Shading feasible region, intersection of half-planes" },
      { topic: "Permutations and Combinations", chapter: "Permutations and Combinations", difficulty: "Hard", hint: "nPr, nCr, circular permutations, identical objects, distinct cases" },
      { topic: "Binomial Theorem — General Term", chapter: "Binomial Theorem", difficulty: "Hard", hint: "T(r+1) = nCr * x^(n-r) * a^r, middle term, coefficient problems" },
      { topic: "Sequences and Series — AP and GP", chapter: "Sequences and Series", difficulty: "Hard", hint: "nth term, sum, AM-GM inequality, sum of infinite GP" },
      { topic: "Straight Lines — Slope and Equations", chapter: "Straight Lines", difficulty: "Hard", hint: "Angle between lines, distance from a point, family of lines" },
      { topic: "Conic Sections — Parabola, Ellipse, Hyperbola", chapter: "Conic Sections", difficulty: "Hard", hint: "Standard forms, focus-directrix, eccentricity, chord of contact" },
      { topic: "Introduction to 3D Geometry", chapter: "Introduction to Three Dimensional Geometry", difficulty: "Tricky", hint: "Distance formula, section formula in 3D, locus problems" },
    ],
  },
  "Grade 12": {
    Physics: [
      { topic: "Electrostatics — Gauss's Law", chapter: "Electric Charges and Fields", difficulty: "Hard", hint: "Flux = q/e0; field due to sheet, sphere, wire; potential energy" },
      { topic: "Current Electricity — Kirchhoff's Laws", chapter: "Current Electricity", difficulty: "Hard", hint: "KVL, KCL, Wheatstone bridge, meter bridge, potentiometer" },
      { topic: "Moving Charges — Biot-Savart Law", chapter: "Moving Charges and Magnetism", difficulty: "Hard", hint: "Field due to circular loop, solenoid, toroid; cyclotron" },
      { topic: "Magnetism — Diamagnetic, Paramagnetic", chapter: "Magnetism and Matter", difficulty: "Tricky", hint: "Hysteresis, B-H curve, magnetic susceptibility, Earth's magnetism" },
      { topic: "Electromagnetic Induction — Faraday's Laws", chapter: "Electromagnetic Induction", difficulty: "Hard", hint: "EMF = -dPhi/dt, Lenz's law, mutual inductance, AC generator" },
      { topic: "Alternating Current — Resonance", chapter: "Alternating Current", difficulty: "Hard", hint: "Impedance, phase diagrams, power factor, Q-factor of LC circuit" },
      { topic: "Electromagnetic Waves — Spectrum", chapter: "Electromagnetic Waves", difficulty: "Tricky", hint: "E and B oscillations, wavelength ranges of EM spectrum" },
      { topic: "Ray Optics — Lens Maker's Equation", chapter: "Ray Optics and Optical Instruments", difficulty: "Hard", hint: "1/f=(n-1)(1/R1-1/R2), dispersion, total internal reflection" },
      { topic: "Wave Optics — Young's Double Slit", chapter: "Wave Optics", difficulty: "Hard", hint: "Fringe width = lambdaD/d, resolving power, polarisation" },
      { topic: "Dual Nature — Photoelectric Effect", chapter: "Dual Nature of Radiation and Matter", difficulty: "Hard", hint: "hv = phi + KE_max, stopping potential, de Broglie wavelength" },
      { topic: "Nuclei — Radioactive Decay Laws", chapter: "Nuclei", difficulty: "Hard", hint: "N=N0*e^(-lambda*t), half-life = 0.693/lambda, Q-value" },
      { topic: "Semiconductor Devices — PN Junction", chapter: "Semiconductor Electronics: Materials, Devices and Simple Circuits", difficulty: "Hard", hint: "Depletion layer, forward/reverse bias, Zener diode, logic gates" },
    ],
    Chemistry: [
      { topic: "Solutions — Colligative Properties", chapter: "Solutions", difficulty: "Hard", hint: "Raoult's law, elevation of BP, depression of FP; van't Hoff factor" },
      { topic: "Electrochemistry — Nernst Equation", chapter: "Electrochemistry", difficulty: "Hard", hint: "E=E0-(RT/nF)lnQ, standard electrode potential, electrolysis" },
      { topic: "Chemical Kinetics — Order and Rate Laws", chapter: "Chemical Kinetics", difficulty: "Hard", hint: "Rate=k[A]^m[B]^n; integrated rate laws; Arrhenius equation" },
      { topic: "Surface Chemistry — Adsorption & Catalysis", chapter: "Surface Chemistry", difficulty: "Tricky", hint: "Physisorption vs chemisorption, Freundlich isotherm" },
      { topic: "d and f Block Elements — Transition Metals", chapter: "The d and f Block Elements", difficulty: "Hard", hint: "Variable oxidation states, magnetic properties, colour" },
      { topic: "Coordination Compounds — IUPAC and VBT", chapter: "Coordination Compounds", difficulty: "Hard", hint: "Nomenclature, isomerism, coordination number, EAN rule" },
      { topic: "Haloalkanes and Haloarenes — SN1 vs SN2", chapter: "Haloalkanes and Haloarenes", difficulty: "Hard", hint: "SN1 vs SN2 mechanism, E1/E2 elimination" },
      { topic: "Alcohols, Phenols and Ethers", chapter: "Alcohols, Phenols and Ethers", difficulty: "Hard", hint: "Acidic strength order, Lucas test, Williamson ether synthesis" },
      { topic: "Aldehydes and Ketones — Nucleophilic Addition", chapter: "Aldehydes, Ketones and Carboxylic Acids", difficulty: "Hard", hint: "Addition of HCN, Grignard; Aldol condensation; Cannizzaro" },
      { topic: "Carboxylic Acids and Derivatives", chapter: "Aldehydes, Ketones and Carboxylic Acids", difficulty: "Hard", hint: "Acidity order, decarboxylation, esterification" },
      { topic: "Amines — Basicity and Reactions", chapter: "Amines", difficulty: "Hard", hint: "Basicity order, Gabriel synthesis, diazotisation" },
      { topic: "Biomolecules — Carbohydrates and Proteins", chapter: "Biomolecules", difficulty: "Tricky", hint: "Reducing sugars, peptide bonds, denaturation, enzyme action" },
    ],
    Biology: [
      { topic: "Reproduction in Organisms", chapter: "Sexual Reproduction in Flowering Plants", difficulty: "Tricky", hint: "Asexual vs sexual, vegetative propagation, sporulation, budding" },
      { topic: "Human Reproduction — Gametogenesis", chapter: "Human Reproduction", difficulty: "Hard", hint: "Spermatogenesis, oogenesis, menstrual cycle, fertilisation" },
      { topic: "Reproductive Health — Contraception", chapter: "Reproductive Health", difficulty: "Medium", hint: "Types of contraception, STIs, MTP, infertility causes" },
      { topic: "Principles of Inheritance — Mendel's Laws", chapter: "Principles of Inheritance and Variation", difficulty: "Hard", hint: "Law of segregation, independent assortment, Punnett square" },
      { topic: "Molecular Basis of Inheritance — DNA", chapter: "Molecular Basis of Inheritance", difficulty: "Hard", hint: "DNA replication, transcription, translation, genetic code" },
      { topic: "Evolution — Darwinism and Speciation", chapter: "Evolution", difficulty: "Tricky", hint: "Natural selection, Hardy-Weinberg, adaptive radiation" },
      { topic: "Human Health and Disease — Immunity", chapter: "Human Health and Disease", difficulty: "Hard", hint: "Innate vs acquired immunity, antibody structure, vaccines" },
      { topic: "Microbes in Human Welfare", chapter: "Microbes in Human Welfare", difficulty: "Tricky", hint: "Biogas, antibiotics, sewage treatment, bioactive molecules" },
      { topic: "Biotechnology — Principles and Processes", chapter: "Biotechnology: Principles and Processes", difficulty: "Hard", hint: "Recombinant DNA, restriction enzymes, PCR, cloning" },
      { topic: "Biotechnology and its Applications", chapter: "Biotechnology and Its Applications", difficulty: "Hard", hint: "Bt cotton, golden rice, insulin production, gene therapy" },
      { topic: "Ecosystem — Productivity and Energy Flow", chapter: "Ecosystem", difficulty: "Hard", hint: "GPP/NPP, ecological pyramids, nutrient cycling, succession" },
      { topic: "Biodiversity and Conservation", chapter: "Biodiversity and Conservation", difficulty: "Tricky", hint: "In-situ vs ex-situ conservation, IUCN categories, hotspots" },
    ],
    Maths: [
      { topic: "Relations and Functions — Inverse and Composition", chapter: "Relations and Functions", difficulty: "Hard", hint: "Bijective for inverse, f∘g vs g∘f, binary operations" },
      { topic: "Inverse Trigonometric Functions", chapter: "Inverse Trigonometric Functions", difficulty: "Hard", hint: "Principal value, domain/range, properties and identities" },
      { topic: "Matrices and Determinants", chapter: "Matrices", difficulty: "Hard", hint: "Row operations, adjoint, inverse matrix, Cramer's rule" },
      { topic: "Continuity and Differentiability", chapter: "Continuity and Differentiability", difficulty: "Hard", hint: "Continuity at a point, chain rule, implicit diff, Rolle's theorem" },
      { topic: "Applications of Derivatives", chapter: "Application of Derivatives", difficulty: "Hard", hint: "Increasing/decreasing, maxima/minima, tangent/normal" },
      { topic: "Integrals — Integration Techniques", chapter: "Integrals", difficulty: "Hard", hint: "Substitution, by parts, partial fractions, special integrals" },
      { topic: "Applications of Integrals — Area", chapter: "Application of Integrals", difficulty: "Hard", hint: "Area between curves, area of circle/ellipse using integration" },
      { topic: "Differential Equations", chapter: "Differential Equations", difficulty: "Hard", hint: "Variable separable, homogeneous, linear DE, integrating factor" },
      { topic: "Vector Algebra — Dot and Cross Product", chapter: "Vector Algebra", difficulty: "Hard", hint: "Magnitude, direction cosines, projection, scalar triple product" },
      { topic: "Three Dimensional Geometry", chapter: "Three Dimensional Geometry", difficulty: "Hard", hint: "Direction cosines, equation of line/plane, angle between lines" },
      { topic: "Linear Programming — Corner Point Method", chapter: "Linear Programming", difficulty: "Tricky", hint: "Feasible region, objective function, graphical solution" },
      { topic: "Probability — Bayes Theorem and Distributions", chapter: "Probability", difficulty: "Hard", hint: "Conditional probability, Bayes theorem, Bernoulli trials" },
    ],
  },
};

const GRADE_LIST = ["Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12"];
const DIFF_COLORS: Record<string, { bg: string; color: string }> = {
  Hard:   { bg: "rgba(239,68,68,.1)",   color: "#ef4444" },
  Tricky: { bg: "rgba(245,158,11,.1)", color: "#f59e0b" },
  Medium: { bg: "rgba(59,130,246,.1)",  color: "#3b82f6" },
};

const MD_STYLES = {
  body: { color: "#1f2937", fontSize: 14, lineHeight: 22 },
  strong: { fontWeight: "700" as const, color: "#111827" },
  bullet_list: { marginVertical: 4 },
  list_item: { marginBottom: 3 },
  paragraph: { marginBottom: 6, lineHeight: 22 },
  heading2: { color: "#111827", fontWeight: "700" as const, fontSize: 15, marginTop: 10, marginBottom: 4 },
};

/** Subjects available for a grade, filtered by stream for Grade 11/12 — mirrors
 * getSubjectsForGrade in frontend/src/pages/ExemplarResearchPage.jsx */
function getSubjectsForGrade(grade: string, stream: string): string[] {
  if (grade === "Grade 11" || grade === "Grade 12") {
    const s = (stream || "").toUpperCase();
    const all = ["Physics", "Chemistry", "Maths", "Biology"];
    if (s === "PCM")  return ["Physics", "Chemistry", "Maths"];
    if (s === "PCB")  return ["Physics", "Chemistry", "Biology"];
    if (s === "PCMB") return all;
    return all; // unknown stream — show all
  }
  return ["Maths", "Science"];
}

/** The Grade 11/12 Exemplar RAG chapters were ingested under subject "Mathematics",
 * not "Maths" (see backend/scripts/upload_ncert_exemplar_grade1112_rag.py
 * FOLDER_TO_SUBJECT), while every other grade/subject uses "Maths". Translate only
 * for the API subject param so /api/doubt/answer's RAG filter actually matches —
 * the UI tab/label keeps using "Maths" everywhere. */
function toRagSubject(grade: string, subject: string): string {
  if ((grade === "Grade 11" || grade === "Grade 12") && subject === "Maths") return "Mathematics";
  return subject;
}

type PracticeQ = { q: string; options: string[]; answer: string; explanation: string };

export default function ExemplarScreen() {
  const router = useRouter();
  const [grade, setGrade]       = useState("Grade 9");
  const [stream, setStream]     = useState("");
  const [subject, setSubject]   = useState("Maths");
  const [diffFilter, setDiff]   = useState("All");
  const [activeTopic, setActive] = useState<TopicCard | null>(null);
  const [explanation, setExpl]  = useState("");
  const [loading, setLoading]   = useState(false);
  const [hasAccess, setHasAccess] = useState(false);
  const explCache = useRef<Record<string, string>>({});

  const [practiceQs, setPracticeQs] = useState<PracticeQ[]>([]);
  const [practiceLoading, setPracticeLoading] = useState(false);
  const [practiceAnswers, setPracticeAnswers] = useState<Record<number, string>>({});
  const [practiceRevealed, setPracticeRevealed] = useState<Record<number, boolean>>({});

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResult, setSearchResult] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);

  useEffect(() => {
    authFetch("/api/auth/me").then((me: any) => setStream(me?.stream ?? "")).catch(() => {});
    authFetch("/api/subscription/features").then((d: any) => {
      setHasAccess(d?.features?.EXEMPLAR_RESEARCH?.allowed ?? d?.has_full_access ?? false);
    }).catch(() => {});
  }, []);

  const subjects = getSubjectsForGrade(grade, stream).filter(sub => !!TOPIC_CARDS[grade]?.[sub]);
  const allTopics = TOPIC_CARDS[grade]?.[subject] ?? [];
  const topics = diffFilter === "All" ? allTopics : allTopics.filter(t => t.difficulty === diffFilter);

  async function explain(topic: TopicCard) {
    setActive(topic);
    setExpl("");
    setPracticeQs([]);
    setPracticeAnswers({});
    setPracticeRevealed({});
    if (!hasAccess) return;
    const key = `${grade}|${subject}|${topic.topic}`;
    if (explCache.current[key]) { setExpl(explCache.current[key]); return; }
    setLoading(true);
    try {
      const res: any = await authFetch("/api/doubt/answer", {
        method: "POST",
        body: JSON.stringify({
          grade, mode: "CBSE", board: "CBSE", subject: toRagSubject(grade, subject), chapter: `Exemplar: ${topic.chapter}`,
          question: "You are a CBSE " + grade + " " + subject + " teacher. Explain the topic: " + topic.topic + " concisely for exam prep. RULES: No diagrams, no LaTeX. Plain text + bullets only.\n\nFormat:\n**What it means**\nOne-sentence definition.\n\n**Key rule / formula**\nState in plain text.\n\n**Solved example**\nBrief step-by-step.\n\n**Exam mistakes to avoid**\n• Mistake 1\n• Mistake 2\n\n**Quick recall tip**\nOne-line memory trick.",
          save_to_history: false,
        }),
      });
      const text = res.answer || "Could not load explanation.";
      explCache.current[key] = text;
      setExpl(text);
    } catch {
      setExpl("Could not load explanation. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function generatePractice(topic: TopicCard) {
    if (!hasAccess) return;
    setPracticeQs([]);
    setPracticeAnswers({});
    setPracticeRevealed({});
    setPracticeLoading(true);

    async function callDoubt(questionText: string): Promise<string> {
      const r: any = await authFetch("/api/doubt/answer", {
        method: "POST",
        body: JSON.stringify({
          grade, mode: "CBSE", board: "CBSE", subject: toRagSubject(grade, subject), chapter: `Exemplar: ${topic.chapter}`,
          question: questionText,
          save_to_history: false,
        }),
      });
      return (r.answer || "").trim();
    }

    try {
      const raw = await callDoubt(
        `Generate exactly 4 NCERT Exemplar-level MCQ practice questions on "${topic.topic}" for CBSE ${grade} ${subject}. Each must be a tricky/HOTS question.

IMPORTANT RULES:
- Do NOT use LaTeX, dollar signs, or math notation. Write all math in plain text (e.g. x^2, P(x), (x-2)(x-3)).
- You MUST include a detailed explanation of at least 3 sentences for EVERY question. NEVER leave explanation blank or short.
- The explanation must show the complete step-by-step working to reach the correct answer.

Respond ONLY with a valid JSON array (no markdown):
[{"q":"...","options":["A) ...","B) ...","C) ...","D) ..."],"answer":"A) ...","explanation":"Step 1: ... Step 2: ... Therefore the answer is A because ..."}]`
      );
      const start = raw.indexOf("["), end = raw.lastIndexOf("]");
      if (start === -1 || end === -1) { setPracticeQs([]); return; }

      let parsed: PracticeQ[];
      try { parsed = JSON.parse(raw.slice(start, end + 1)); } catch { setPracticeQs([]); return; }

      let cleanedQs = parsed;
      const needsExplanations = cleanedQs.some(q => !q.explanation || q.explanation.length < 40);
      if (needsExplanations) {
        const questionsText = cleanedQs
          .map((q, i) => `Q${i + 1}: ${q.q}\nCorrect answer: ${q.answer}`)
          .join("\n\n");

        const explRaw = await callDoubt(
          `For each of these ${subject} questions about "${topic.topic}" (Grade ${grade}), provide a detailed explanation of at least 3 sentences showing the complete working.

${questionsText}

Do NOT use dollar signs or LaTeX. Write all math in plain text.
Respond ONLY with a JSON array of exactly ${cleanedQs.length} explanation strings:
["Full explanation for Q1 showing step by step working...", "Full explanation for Q2...", ...]`
        );
        const es = explRaw.indexOf("["), ee = explRaw.lastIndexOf("]");
        if (es !== -1 && ee !== -1) {
          try {
            const explanations = JSON.parse(explRaw.slice(es, ee + 1));
            cleanedQs = cleanedQs.map((q, i) => ({
              ...q,
              explanation: (explanations[i] && typeof explanations[i] === "string") ? explanations[i] : q.explanation,
            }));
          } catch { /* keep existing explanations */ }
        }
      }

      setPracticeQs(cleanedQs);
    } catch {
      setPracticeQs([]);
    } finally {
      setPracticeLoading(false);
    }
  }

  async function handleSearch() {
    if (!searchQuery.trim()) return;
    if (!hasAccess) { setSearchResult("__upgrade__"); return; }
    setSearchResult("");
    setSearchLoading(true);
    try {
      const res: any = await authFetch("/api/doubt/answer", {
        method: "POST",
        body: JSON.stringify({
          grade, mode: "CBSE", board: "CBSE", subject: toRagSubject(grade, subject), chapter: searchQuery,
          question: `Explain "${searchQuery}" for a CBSE ${grade} ${subject} student in detail. Include definition, key concept, example, and what to watch out for in exams.`,
          save_to_history: false,
        }),
      });
      setSearchResult(res.answer || "No explanation found.");
    } catch {
      setSearchResult("Search failed. Please try again.");
    } finally {
      setSearchLoading(false);
    }
  }

  return (
    <ScrollView style={s.container} contentContainerStyle={s.content}>
      <View style={s.pageHeader}>
        <TouchableOpacity style={s.backBtn} onPress={() => router.back()}>
          <Feather name="arrow-left" size={18} color={BRAND_COLOR} />
        </TouchableOpacity>
        <View style={[s.pageIconBox, { backgroundColor: "rgba(99,102,241,.08)" }]}>
          <Feather name="layers" size={20} color={BRAND_COLOR} />
        </View>
        <View>
          <Text style={s.pageTitle}>Exemplar Research</Text>
          <Text style={s.pageSubtitle}>NCERT Exemplar topics with AI explanations</Text>
        </View>
      </View>

      {/* Grade selector */}
      <Text style={s.label}>Grade</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.chipRow}>
        {GRADE_LIST.map(g => (
          <TouchableOpacity key={g} style={[s.chip, grade === g && s.chipActive]}
            onPress={() => {
              setGrade(g);
              setSubject(getSubjectsForGrade(g, stream).filter(sub => !!TOPIC_CARDS[g]?.[sub])[0] ?? "Maths");
              setActive(null); setExpl("");
            }}>
            <Text style={[s.chipText, grade === g && s.chipTextActive]}>{g.replace("Grade ", "")}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Subject tabs */}
      <Text style={s.label}>Subject</Text>
      <View style={s.subjectRow}>
        {subjects.map(sub => (
          <TouchableOpacity key={sub} style={[s.subjectBtn, subject === sub && s.subjectBtnActive]}
            onPress={() => { setSubject(sub); setActive(null); setExpl(""); }}>
            <Text style={[s.subjectBtnText, subject === sub && s.subjectBtnTextActive]}>{sub}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Difficulty filter */}
      <View style={s.filterRow}>
        {["All","Hard","Tricky","Medium"].map(d => (
          <TouchableOpacity key={d} style={[s.filterChip, diffFilter === d && s.filterChipActive]} onPress={() => setDiff(d)}>
            <Text style={[s.filterChipText, diffFilter === d && s.filterChipTextActive]}>{d}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Search bar */}
      <Text style={s.label}>Search any {subject} topic</Text>
      <View style={s.searchRow}>
        <TextInput
          style={s.searchInput}
          placeholder={`e.g. "Ohm's Law" or "Quadratic Formula"`}
          placeholderTextColor="#9ca3af"
          value={searchQuery}
          onChangeText={setSearchQuery}
          onSubmitEditing={handleSearch}
          returnKeyType="search"
        />
        <TouchableOpacity
          style={[s.searchBtn, (searchLoading || !searchQuery.trim()) && s.searchBtnDisabled]}
          onPress={handleSearch}
          disabled={searchLoading || !searchQuery.trim()}
        >
          {searchLoading
            ? <ActivityIndicator color="#fff" size="small" />
            : <Feather name="search" size={16} color="#fff" />}
        </TouchableOpacity>
      </View>

      {/* Search result (or upgrade gate) */}
      {searchResult === "__upgrade__" ? (
        <View style={[s.upgradeBanner, { marginTop: 0, marginBottom: 16 }]}>
          <Text style={s.upgradeBannerIcon}>🔒</Text>
          <View style={{ flex: 1 }}>
            <Text style={s.upgradeBannerTitle}>Premium Feature</Text>
            <Text style={s.upgradeBannerText}>Topic search is available on Premium plans. Upgrade to search any topic.</Text>
          </View>
        </View>
      ) : searchResult ? (
        <View style={s.searchResultCard}>
          <View style={s.searchResultHeader}>
            <Text style={s.searchResultTitle} numberOfLines={1}>🔍 {searchQuery}</Text>
            <TouchableOpacity onPress={() => { setSearchResult(""); setSearchQuery(""); }}>
              <Feather name="x" size={16} color="#6b7280" />
            </TouchableOpacity>
          </View>
          <Markdown style={MD_STYLES}>{searchResult}</Markdown>
        </View>
      ) : null}

      {/* Topic count */}
      <Text style={s.topicCount}>{topics.length} topics · tap any to get AI explanation</Text>

      {/* Topic cards */}
      {topics.map((t, i) => {
        const dc = DIFF_COLORS[t.difficulty] ?? DIFF_COLORS.Medium;
        const isActive = activeTopic?.topic === t.topic;
        return (
          <View key={i}>
            <TouchableOpacity style={[s.topicCard, isActive && s.topicCardActive]} onPress={() => explain(t)}>
              <View style={{ flex: 1 }}>
                <View style={s.topicCardHeader}>
                  <Text style={s.topicName}>{t.topic}</Text>
                  <View style={[s.diffBadge, { backgroundColor: dc.bg }]}>
                    <Text style={[s.diffText, { color: dc.color }]}>{t.difficulty}</Text>
                  </View>
                </View>
                <Text style={s.topicHint}>{t.hint}</Text>
              </View>
              <Feather name={isActive ? "chevron-up" : "chevron-down"} size={16} color="#9ca3af" />
            </TouchableOpacity>

            {/* Explanation panel */}
            {isActive && (
              <View style={s.explPanel}>
                {!hasAccess ? (
                  <View style={s.upgradeBanner}>
                    <Text style={s.upgradeBannerIcon}>🔒</Text>
                    <View style={{ flex: 1 }}>
                      <Text style={s.upgradeBannerTitle}>Premium Feature</Text>
                      <Text style={s.upgradeBannerText}>Exemplar topic explanations are available on Premium plans. Upgrade to unlock AI explanations for all topics.</Text>
                    </View>
                  </View>
                ) : loading && !explanation ? (
                  <View style={{ flexDirection: "row", alignItems: "center", gap: 10, padding: 12 }}>
                    <ActivityIndicator color={BRAND_COLOR} size="small" />
                    <Text style={{ color: "#6b7280", fontSize: 13 }}>Loading explanation…</Text>
                  </View>
                ) : explanation ? (
                  <View style={{ padding: 14 }}>
                    <Markdown style={MD_STYLES}>{explanation}</Markdown>
                    <TouchableOpacity style={s.ncertBtn} onPress={() => Linking.openURL("https://ncert.nic.in/exemplar-problems.php")}>
                      <Feather name="external-link" size={13} color="#10b981" />
                      <Text style={s.ncertBtnText}>Browse Exemplar Problems</Text>
                    </TouchableOpacity>

                    {/* ── Generate Practice Questions ── */}
                    <TouchableOpacity
                      style={[s.practiceBtn, practiceLoading && s.practiceBtnDisabled]}
                      onPress={() => generatePractice(t)}
                      disabled={practiceLoading}
                    >
                      {practiceLoading
                        ? <ActivityIndicator color="#fff" size="small" />
                        : <><Feather name="target" size={14} color="#fff" /><Text style={s.practiceBtnText}>Generate Practice Questions</Text></>}
                    </TouchableOpacity>

                    {/* ── Inline MCQ practice panel ── */}
                    {practiceQs.length > 0 && (
                      <View style={{ marginTop: 14, gap: 12 }}>
                        <Text style={s.practiceHeading}>🎯 {practiceQs.length} Practice Questions · {t.topic}</Text>
                        {practiceQs.map((q, qi) => {
                          const selected = practiceAnswers[qi];
                          const revealed = practiceRevealed[qi];
                          const isCorrectAnswer = selected === q.answer;
                          return (
                            <View key={qi} style={s.practiceCard}>
                              <Text style={s.practiceQText}>Q{qi + 1}. {q.q}</Text>
                              <View style={{ gap: 6 }}>
                                {(q.options || []).map((opt, oi) => {
                                  const isCorrect = opt === q.answer;
                                  const isSelected = selected === opt;
                                  let style = s.optionDefault;
                                  if (revealed && isCorrect) style = s.optionCorrect;
                                  else if (revealed && isSelected && !isCorrect) style = s.optionWrong;
                                  else if (!revealed && isSelected) style = s.optionSelected;
                                  return (
                                    <TouchableOpacity
                                      key={oi}
                                      style={[s.optionBase, style]}
                                      disabled={revealed}
                                      onPress={() => setPracticeAnswers(p => ({ ...p, [qi]: opt }))}
                                    >
                                      <Text style={s.optionBaseText}>{opt}</Text>
                                    </TouchableOpacity>
                                  );
                                })}
                              </View>
                              {!revealed && selected && (
                                <TouchableOpacity style={s.checkBtn} onPress={() => setPracticeRevealed(p => ({ ...p, [qi]: true }))}>
                                  <Text style={s.checkBtnText}>Check Answer</Text>
                                </TouchableOpacity>
                              )}
                              {revealed && (
                                <View style={{ marginTop: 6 }}>
                                  <Text style={[s.resultText, { color: isCorrectAnswer ? "#10b981" : "#ef4444" }]}>
                                    {isCorrectAnswer ? "✅ Correct!" : `❌ Incorrect — correct: ${q.answer}`}
                                  </Text>
                                  <View style={s.explainBox}>
                                    <Text style={s.explainLabel}>💡 Explanation</Text>
                                    <Text style={s.explainBody}>
                                      {q.explanation || `The correct answer is ${q.answer}. Review the concept of ${t.topic} and work through this problem step by step.`}
                                    </Text>
                                  </View>
                                </View>
                              )}
                            </View>
                          );
                        })}
                      </View>
                    )}
                  </View>
                ) : null}
              </View>
            )}
          </View>
        );
      })}

      {/* NCERT link at bottom */}
      <TouchableOpacity style={s.bottomLink} onPress={() => Linking.openURL("https://ncert.nic.in/exemplar-problems.php")}>
        <Feather name="external-link" size={16} color={BRAND_COLOR} />
        <Text style={s.bottomLinkText}>Browse All NCERT Exemplar Books →</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  content: { padding: 16, paddingBottom: 60 },
  pageHeader: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 20 },
  backBtn: { padding: 8, borderRadius: 8, backgroundColor: "rgba(99,102,241,.08)" },
  pageIconBox: { width: 44, height: 44, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  pageTitle: { fontSize: 20, fontWeight: "800", color: "#111827" },
  pageSubtitle: { fontSize: 13, color: "#6b7280", lineHeight: 19 },
  label: { fontSize: 11, fontWeight: "700", color: "#6b7280", textTransform: "uppercase", letterSpacing: 0.6, marginBottom: 8, marginTop: 14 },
  chipRow: { flexDirection: "row", marginBottom: 4 },
  chip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 99, borderWidth: 1.5, borderColor: "#d1d5db", backgroundColor: "#fff", marginRight: 8 },
  chipActive: { borderColor: BRAND_COLOR, backgroundColor: BRAND_COLOR },
  chipText: { fontSize: 12, fontWeight: "600", color: "#374151" },
  chipTextActive: { color: "#fff" },
  subjectRow: { flexDirection: "row", gap: 8, flexWrap: "wrap", marginBottom: 14 },
  subjectBtn: { paddingHorizontal: 16, paddingVertical: 9, borderRadius: 10, borderWidth: 1.5, borderColor: "#d1d5db", backgroundColor: "#fff" },
  subjectBtnActive: { borderColor: BRAND_COLOR, backgroundColor: BRAND_COLOR },
  subjectBtnText: { fontSize: 13, fontWeight: "700", color: "#374151" },
  subjectBtnTextActive: { color: "#fff" },
  filterRow: { flexDirection: "row", gap: 7, marginBottom: 10, flexWrap: "wrap" },
  filterChip: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 99, borderWidth: 1, borderColor: "#d1d5db", backgroundColor: "#fff" },
  filterChipActive: { borderColor: BRAND_COLOR, backgroundColor: "rgba(99,102,241,.08)" },
  filterChipText: { fontSize: 11, fontWeight: "600", color: "#6b7280" },
  filterChipTextActive: { color: BRAND_COLOR },
  topicCount: { fontSize: 11, color: "#9ca3af", marginBottom: 12, fontWeight: "600" },
  topicCard: { flexDirection: "row", alignItems: "flex-start", backgroundColor: "#fff", borderRadius: 12, padding: 14, marginBottom: 2, borderWidth: 1, borderColor: "#e5e7eb", gap: 10 },
  topicCardActive: { borderColor: BRAND_COLOR, backgroundColor: "rgba(99,102,241,.03)" },
  topicCardHeader: { flexDirection: "row", alignItems: "flex-start", gap: 8, marginBottom: 4, flexWrap: "wrap" },
  topicName: { fontSize: 14, fontWeight: "700", color: "#111827", flex: 1 },
  topicHint: { fontSize: 11, color: "#6b7280", lineHeight: 17 },
  upgradeBanner: { flexDirection: "row", alignItems: "flex-start", gap: 10, backgroundColor: "rgba(99,102,241,.07)", borderRadius: 12, padding: 14, margin: 14 },
  upgradeBannerIcon: { fontSize: 20, marginTop: 1 },
  upgradeBannerTitle: { fontSize: 13, fontWeight: "800", color: "#6366f1", marginBottom: 3 },
  upgradeBannerText: { fontSize: 12, color: "#374151", lineHeight: 18 },
  diffBadge: { borderRadius: 99, paddingHorizontal: 8, paddingVertical: 2, flexShrink: 0 },
  diffText: { fontSize: 10, fontWeight: "700" },
  explPanel: { backgroundColor: "#f8fafc", borderRadius: "0 0 12px 12px" as any, borderWidth: 1, borderTopWidth: 0, borderColor: BRAND_COLOR, marginBottom: 8 },
  ncertBtn: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 12 },
  ncertBtnText: { fontSize: 12, fontWeight: "700", color: "#10b981" },
  bottomLink: { flexDirection: "row", alignItems: "center", gap: 8, justifyContent: "center", marginTop: 24, padding: 14, backgroundColor: "rgba(99,102,241,.06)", borderRadius: 12, borderWidth: 1, borderColor: "rgba(99,102,241,.2)" },
  bottomLinkText: { fontSize: 13, fontWeight: "700", color: BRAND_COLOR },
  // Search bar
  searchRow: { flexDirection: "row", gap: 8, marginBottom: 14 },
  searchInput: { flex: 1, paddingHorizontal: 14, paddingVertical: 10, borderRadius: 10, borderWidth: 1.5, borderColor: "#d1d5db", backgroundColor: "#fff", fontSize: 13, color: "#111827" },
  searchBtn: { width: 42, alignItems: "center", justifyContent: "center", borderRadius: 10, backgroundColor: BRAND_COLOR },
  searchBtnDisabled: { opacity: 0.5 },
  searchResultCard: { backgroundColor: "#fff", borderRadius: 12, padding: 14, marginBottom: 16, borderWidth: 1, borderColor: "#e5e7eb", borderLeftWidth: 3, borderLeftColor: BRAND_COLOR },
  searchResultHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  searchResultTitle: { fontSize: 13, fontWeight: "800", color: BRAND_COLOR, flex: 1, marginRight: 8 },
  // Practice questions
  practiceBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, marginTop: 14, paddingVertical: 10, borderRadius: 10, backgroundColor: "#059669" },
  practiceBtnDisabled: { opacity: 0.6 },
  practiceBtnText: { fontSize: 13, fontWeight: "700", color: "#fff" },
  practiceHeading: { fontSize: 11, fontWeight: "800", color: "#10b981", textTransform: "uppercase", letterSpacing: 0.6 },
  practiceCard: { padding: 12, borderRadius: 10, backgroundColor: "rgba(16,185,129,.06)", borderWidth: 1, borderColor: "rgba(16,185,129,.2)" },
  practiceQText: { fontWeight: "700", fontSize: 13, marginBottom: 8, color: "#111827", lineHeight: 19 },
  optionBase: { paddingHorizontal: 10, paddingVertical: 7, borderRadius: 7 },
  optionBaseText: { fontSize: 12.5, color: "#111827" },
  optionDefault: { borderWidth: 1, borderColor: "#e5e7eb", backgroundColor: "#fff" },
  optionSelected: { borderWidth: 1, borderColor: BRAND_COLOR, backgroundColor: "rgba(99,102,241,.1)" },
  optionCorrect: { borderWidth: 1, borderColor: "#10b981", backgroundColor: "rgba(16,185,129,.15)" },
  optionWrong: { borderWidth: 1, borderColor: "#ef4444", backgroundColor: "rgba(239,68,68,.1)" },
  checkBtn: { alignSelf: "flex-start", marginTop: 8, paddingHorizontal: 12, paddingVertical: 5, borderRadius: 7, backgroundColor: "#10b981" },
  checkBtnText: { fontSize: 12, fontWeight: "700", color: "#fff" },
  resultText: { fontSize: 12, fontWeight: "700", marginBottom: 6 },
  explainBox: { padding: 10, borderRadius: 8, backgroundColor: "rgba(37,99,235,.06)", borderWidth: 1, borderColor: "rgba(37,99,235,.2)" },
  explainLabel: { fontSize: 12, fontWeight: "700", color: "#2563eb", marginBottom: 4 },
  explainBody: { fontSize: 12, color: "#374151", lineHeight: 18 },
});
