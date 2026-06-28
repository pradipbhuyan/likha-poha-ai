"""
seed_formula_sheets.py
─────────────────────────────────────────────────────────────────────────────
Seed CBSE formula sheets for Grade 5-10 (Mathematics + Science).
Run after applying the migration:
  cd backend && python scripts/seed_formula_sheets.py

Idempotent: checks for existing rows per grade+subject before inserting.
─────────────────────────────────────────────────────────────────────────────
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.auth_service import admin_client

FORMULAS = [
    # ── Grade 5 Mathematics ──────────────────────────────────────────────────
    {"grade":"Grade 5","subject":"Mathematics","chapter":"Shapes","section_title":"Area & Perimeter",
     "formula_name":"Perimeter of Rectangle","expression":"P = 2 × (l + b)",
     "explanation":"l = length, b = breadth","example":"l=5, b=3 → P=16","display_order":1},
    {"grade":"Grade 5","subject":"Mathematics","chapter":"Shapes","section_title":"Area & Perimeter",
     "formula_name":"Area of Rectangle","expression":"A = l × b",
     "explanation":"Multiply length by breadth","example":"l=5, b=3 → A=15","display_order":2},
    {"grade":"Grade 5","subject":"Mathematics","chapter":"Shapes","section_title":"Area & Perimeter",
     "formula_name":"Perimeter of Square","expression":"P = 4 × a",
     "explanation":"a = side length","example":"a=4 → P=16","display_order":3},
    {"grade":"Grade 5","subject":"Mathematics","chapter":"Shapes","section_title":"Area & Perimeter",
     "formula_name":"Area of Square","expression":"A = a²",
     "explanation":"Square of side length","example":"a=4 → A=16","display_order":4},

    # ── Grade 6 Mathematics ──────────────────────────────────────────────────
    {"grade":"Grade 6","subject":"Mathematics","chapter":"Mensuration","section_title":"Perimeter & Area",
     "formula_name":"Perimeter of Triangle","expression":"P = a + b + c",
     "explanation":"Sum of all three sides","example":"a=3,b=4,c=5 → P=12","display_order":1},
    {"grade":"Grade 6","subject":"Mathematics","chapter":"Mensuration","section_title":"Perimeter & Area",
     "formula_name":"Area of Triangle","expression":"A = (1/2) × b × h",
     "explanation":"b=base, h=perpendicular height","example":"b=6, h=4 → A=12","display_order":2},
    {"grade":"Grade 6","subject":"Mathematics","chapter":"Algebra","section_title":"Basic Algebra",
     "formula_name":"Simple Interest","expression":"SI = (P × R × T) / 100",
     "explanation":"P=principal, R=rate%, T=time in years","example":"P=1000,R=5,T=2 → SI=100","display_order":3},

    # ── Grade 7 Mathematics ──────────────────────────────────────────────────
    {"grade":"Grade 7","subject":"Mathematics","chapter":"Triangles","section_title":"Triangle Properties",
     "formula_name":"Pythagoras Theorem","expression":"a² + b² = c²",
     "explanation":"In a right triangle, c is the hypotenuse","example":"a=3,b=4 → c=5","display_order":1},
    {"grade":"Grade 7","subject":"Mathematics","chapter":"Mensuration","section_title":"Area & Volume",
     "formula_name":"Area of Circle","expression":"A = π r²",
     "explanation":"r = radius, π ≈ 3.14159","example":"r=7 → A=154","display_order":2},
    {"grade":"Grade 7","subject":"Mathematics","chapter":"Mensuration","section_title":"Area & Volume",
     "formula_name":"Circumference of Circle","expression":"C = 2πr",
     "explanation":"r = radius","example":"r=7 → C=44","display_order":3},
    {"grade":"Grade 7","subject":"Mathematics","chapter":"Ratio & Proportion","section_title":"Proportion",
     "formula_name":"Percentage","expression":"% = (Part / Whole) × 100",
     "explanation":"Convert fraction to percentage","example":"25/50 × 100 = 50%","display_order":4},

    # ── Grade 8 Mathematics ──────────────────────────────────────────────────
    {"grade":"Grade 8","subject":"Mathematics","chapter":"Mensuration","section_title":"3D Solids",
     "formula_name":"Volume of Cuboid","expression":"V = l × b × h",
     "explanation":"l=length, b=breadth, h=height","example":"l=3,b=4,h=5 → V=60","display_order":1},
    {"grade":"Grade 8","subject":"Mathematics","chapter":"Mensuration","section_title":"3D Solids",
     "formula_name":"Surface Area of Cuboid","expression":"SA = 2(lb + bh + hl)",
     "explanation":"Sum of areas of all 6 faces","example":"l=3,b=4,h=5 → SA=94","display_order":2},
    {"grade":"Grade 8","subject":"Mathematics","chapter":"Mensuration","section_title":"3D Solids",
     "formula_name":"Volume of Cylinder","expression":"V = πr²h",
     "explanation":"r=radius, h=height","example":"r=7,h=10 → V=1540","display_order":3},
    {"grade":"Grade 8","subject":"Mathematics","chapter":"Algebra","section_title":"Identities",
     "formula_name":"(a+b)²","expression":"(a+b)² = a² + 2ab + b²",
     "explanation":"Square of sum expansion","example":"(x+3)²=x²+6x+9","display_order":4},
    {"grade":"Grade 8","subject":"Mathematics","chapter":"Algebra","section_title":"Identities",
     "formula_name":"(a-b)²","expression":"(a-b)² = a² - 2ab + b²",
     "explanation":"Square of difference expansion","example":"(x-3)²=x²-6x+9","display_order":5},
    {"grade":"Grade 8","subject":"Mathematics","chapter":"Algebra","section_title":"Identities",
     "formula_name":"(a+b)(a-b)","expression":"(a+b)(a-b) = a² - b²",
     "explanation":"Difference of squares","example":"(x+3)(x-3)=x²-9","display_order":6},

    # ── Grade 9 Mathematics ──────────────────────────────────────────────────
    {"grade":"Grade 9","subject":"Mathematics","chapter":"Triangles","section_title":"Congruence & Area",
     "formula_name":"Heron's Formula","expression":"A = √[s(s-a)(s-b)(s-c)]",
     "explanation":"s=(a+b+c)/2 is semi-perimeter","example":"a=3,b=4,c=5: s=6 → A=6","display_order":1},
    {"grade":"Grade 9","subject":"Mathematics","chapter":"Circles","section_title":"Circle Formulas",
     "formula_name":"Area of Circle","expression":"A = πr²",
     "explanation":"r = radius","example":"r=14 → A=616","display_order":2},
    {"grade":"Grade 9","subject":"Mathematics","chapter":"Circles","section_title":"Circle Formulas",
     "formula_name":"Arc Length","expression":"l = (θ/360) × 2πr",
     "explanation":"θ=central angle in degrees","example":"θ=90,r=7 → l=11","display_order":3},
    {"grade":"Grade 9","subject":"Mathematics","chapter":"Statistics","section_title":"Central Tendency",
     "formula_name":"Mean","expression":"x̄ = Σx / n",
     "explanation":"Sum of observations divided by count","example":"[2,4,6]: x̄=4","display_order":4},
    {"grade":"Grade 9","subject":"Mathematics","chapter":"Probability","section_title":"Basic Probability",
     "formula_name":"Probability","expression":"P(E) = n(E) / n(S)",
     "explanation":"n(E)=favourable outcomes, n(S)=total outcomes","example":"P(Head)=1/2","display_order":5},
    {"grade":"Grade 9","subject":"Mathematics","chapter":"Coordinate Geometry","section_title":"Distance & Midpoint",
     "formula_name":"Distance Formula","expression":"d = √[(x₂-x₁)² + (y₂-y₁)²]",
     "explanation":"Distance between two points","example":"(0,0)→(3,4): d=5","display_order":6},
    {"grade":"Grade 9","subject":"Mathematics","chapter":"Coordinate Geometry","section_title":"Distance & Midpoint",
     "formula_name":"Section Formula (Midpoint)","expression":"M = ((x₁+x₂)/2, (y₁+y₂)/2)",
     "explanation":"Midpoint of a line segment","example":"(0,0)&(4,6) → M=(2,3)","display_order":7},

    # ── Grade 9 Science ───────────────────────────────────────────────────────
    {"grade":"Grade 9","subject":"Science","chapter":"Motion","section_title":"Equations of Motion",
     "formula_name":"First Equation of Motion","expression":"v = u + at",
     "explanation":"v=final velocity, u=initial velocity, a=acceleration, t=time","example":"u=0,a=10,t=5 → v=50","display_order":1},
    {"grade":"Grade 9","subject":"Science","chapter":"Motion","section_title":"Equations of Motion",
     "formula_name":"Second Equation of Motion","expression":"s = ut + (1/2)at²",
     "explanation":"s=displacement","example":"u=0,a=10,t=3 → s=45","display_order":2},
    {"grade":"Grade 9","subject":"Science","chapter":"Motion","section_title":"Equations of Motion",
     "formula_name":"Third Equation of Motion","expression":"v² = u² + 2as",
     "explanation":"Relates velocity, acceleration, displacement","example":"u=0,a=10,s=20 → v=20","display_order":3},
    {"grade":"Grade 9","subject":"Science","chapter":"Force","section_title":"Newton's Laws",
     "formula_name":"Newton's Second Law","expression":"F = ma",
     "explanation":"F=force(N), m=mass(kg), a=acceleration(m/s²)","example":"m=5kg,a=3 → F=15N","display_order":4},
    {"grade":"Grade 9","subject":"Science","chapter":"Force","section_title":"Newton's Laws",
     "formula_name":"Momentum","expression":"p = mv",
     "explanation":"p=momentum(kg·m/s), m=mass, v=velocity","example":"m=2kg,v=5 → p=10","display_order":5},
    {"grade":"Grade 9","subject":"Science","chapter":"Work & Energy","section_title":"Work, Energy, Power",
     "formula_name":"Work Done","expression":"W = F × d × cos θ",
     "explanation":"F=force, d=displacement, θ=angle between F and d","example":"F=10N,d=5m,θ=0 → W=50J","display_order":6},
    {"grade":"Grade 9","subject":"Science","chapter":"Work & Energy","section_title":"Work, Energy, Power",
     "formula_name":"Kinetic Energy","expression":"KE = (1/2)mv²",
     "explanation":"m=mass, v=velocity","example":"m=2kg,v=4 → KE=16J","display_order":7},
    {"grade":"Grade 9","subject":"Science","chapter":"Work & Energy","section_title":"Work, Energy, Power",
     "formula_name":"Potential Energy","expression":"PE = mgh",
     "explanation":"m=mass, g=9.8m/s², h=height","example":"m=2,h=5 → PE=98J","display_order":8},
    {"grade":"Grade 9","subject":"Science","chapter":"Work & Energy","section_title":"Work, Energy, Power",
     "formula_name":"Power","expression":"P = W / t",
     "explanation":"P=power(W), W=work(J), t=time(s)","example":"W=100J,t=5s → P=20W","display_order":9},
    {"grade":"Grade 9","subject":"Science","chapter":"Gravitation","section_title":"Gravity",
     "formula_name":"Universal Gravitation","expression":"F = G·m₁·m₂ / r²",
     "explanation":"G=6.674×10⁻¹¹, r=distance between centres","example":"Gravitational attraction between two masses","display_order":10},

    # ── Grade 10 Mathematics ─────────────────────────────────────────────────
    {"grade":"Grade 10","subject":"Mathematics","chapter":"Quadratic Equations","section_title":"Solving Quadratics",
     "formula_name":"Quadratic Formula","expression":"x = [-b ± √(b²-4ac)] / 2a",
     "explanation":"For ax²+bx+c=0","example":"x²-5x+6=0: a=1,b=-5,c=6 → x=3,2","display_order":1},
    {"grade":"Grade 10","subject":"Mathematics","chapter":"Quadratic Equations","section_title":"Solving Quadratics",
     "formula_name":"Discriminant","expression":"D = b² - 4ac",
     "explanation":"D>0: 2 roots; D=0: 1 root; D<0: no real roots","example":"b²-4ac=0 → equal roots","display_order":2},
    {"grade":"Grade 10","subject":"Mathematics","chapter":"Arithmetic Progression","section_title":"AP Formulas",
     "formula_name":"nth Term of AP","expression":"aₙ = a + (n-1)d",
     "explanation":"a=first term, d=common difference, n=term number","example":"a=2,d=3,n=5 → a₅=14","display_order":3},
    {"grade":"Grade 10","subject":"Mathematics","chapter":"Arithmetic Progression","section_title":"AP Formulas",
     "formula_name":"Sum of n Terms of AP","expression":"Sₙ = (n/2)[2a + (n-1)d]",
     "explanation":"Sum of first n terms","example":"a=1,d=1,n=10 → S₁₀=55","display_order":4},
    {"grade":"Grade 10","subject":"Mathematics","chapter":"Trigonometry","section_title":"Trigonometric Ratios",
     "formula_name":"sin θ","expression":"sin θ = Opposite / Hypotenuse",
     "explanation":"In a right triangle","example":"In 3-4-5 triangle: sin θ=3/5=0.6","display_order":5},
    {"grade":"Grade 10","subject":"Mathematics","chapter":"Trigonometry","section_title":"Trigonometric Ratios",
     "formula_name":"cos θ","expression":"cos θ = Adjacent / Hypotenuse",
     "explanation":"In a right triangle","example":"In 3-4-5 triangle: cos θ=4/5=0.8
","display_order":6},
    {"grade":"Grade 10","subject":"Mathematics","chapter":"Trigonometry","section_title":"Trigonometric Ratios",
     "formula_name":"tan θ","expression":"tan θ = Opposite / Adjacent = sin θ / cos θ",
     "explanation":"In a right triangle","example":"In 3-4-5 triangle: tan θ=3/4=0.75","display_order":7},
    {"grade":"Grade 10","subject":"Mathematics","chapter":"Trigonometry","section_title":"Identities",
     "formula_name":"Pythagorean Identity","expression":"sin²θ + cos²θ = 1",
     "explanation":"Fundamental trig identity","example":"sin²30+cos²30=0.25+0.75=1","display_order":8},
    {"grade":"Grade 10","subject":"Mathematics","chapter":"Circles","section_title":"Tangent & Chord",
     "formula_name":"Tangent-Radius","expression":"OT ⊥ PT  (angle = 90°)",
     "explanation":"Tangent to a circle is perpendicular to radius at point of contact","example":"OT=5, PT=12 → OP=13","display_order":9},
    {"grade":"Grade 10","subject":"Mathematics","chapter":"Surface Area & Volume","section_title":"3D Mensuration",
     "formula_name":"Volume of Cone","expression":"V = (1/3)πr²h",
     "explanation":"r=base radius, h=height","example":"r=7,h=3 → V=154","display_order":10},
    {"grade":"Grade 10","subject":"Mathematics","chapter":"Surface Area & Volume","section_title":"3D Mensuration",
     "formula_name":"Volume of Sphere","expression":"V = (4/3)πr³",
     "explanation":"r=radius","example":"r=3 → V=113.1","display_order":11},
    {"grade":"Grade 10","subject":"Mathematics","chapter":"Surface Area & Volume","section_title":"3D Mensuration",
     "formula_name":"Curved Surface Area of Cylinder","expression":"CSA = 2πrh",
     "explanation":"r=radius, h=height","example":"r=7,h=10 → CSA=440","display_order":12},

    # ── Grade 10 Science ───────────────────────────────────────────────────────
    {"grade":"Grade 10","subject":"Science","chapter":"Light","section_title":"Optics",
     "formula_name":"Mirror Formula","expression":"1/f = 1/v + 1/u",
     "explanation":"f=focal length, v=image distance, u=object distance","example":"u=-30,f=-10 → v=-15","display_order":1},
    {"grade":"Grade 10","subject":"Science","chapter":"Light","section_title":"Optics",
     "formula_name":"Magnification (Mirror)","expression":"m = -v/u = h'/h",
     "explanation":"h'=image height, h=object height","example":"v=-15,u=-30 → m=0.5","display_order":2},
    {"grade":"Grade 10","subject":"Science","chapter":"Light","section_title":"Optics",
     "formula_name":"Lens Formula","expression":"1/f = 1/v - 1/u",
     "explanation":"For convex/concave lens","example":"u=-20,f=10 → v=20","display_order":3},
    {"grade":"Grade 10","subject":"Science","chapter":"Light","section_title":"Optics",
     "formula_name":"Snell's Law","expression":"n₁ sin θ₁ = n₂ sin θ₂",
     "explanation":"Refraction at interface of two media","example":"n₁=1,θ₁=30°,n₂=1.5 → θ₂≈19.5°","display_order":4},
    {"grade":"Grade 10","subject":"Science","chapter":"Electricity","section_title":"Ohm's Law & Circuits",
     "formula_name":"Ohm's Law","expression":"V = IR",
     "explanation":"V=voltage(V), I=current(A), R=resistance(Ω)","example":"I=2A,R=5Ω → V=10V","display_order":5},
    {"grade":"Grade 10","subject":"Science","chapter":"Electricity","section_title":"Ohm's Law & Circuits",
     "formula_name":"Electric Power","expression":"P = VI = I²R = V²/R",
     "explanation":"Power consumed by resistor","example":"V=10,I=2 → P=20W","display_order":6},
    {"grade":"Grade 10","subject":"Science","chapter":"Electricity","section_title":"Ohm's Law & Circuits",
     "formula_name":"Resistors in Series","expression":"R_total = R₁ + R₂ + R₃ ...",
     "explanation":"Series circuit: resistances add up","example":"R₁=2,R₂=3 → R=5Ω","display_order":7},
    {"grade":"Grade 10","subject":"Science","chapter":"Electricity","section_title":"Ohm's Law & Circuits",
     "formula_name":"Resistors in Parallel","expression":"1/R_total = 1/R₁ + 1/R₂ ...",
     "explanation":"Parallel circuit: reciprocals add","example":"R₁=4,R₂=4 → R=2Ω","display_order":8},
    {"grade":"Grade 10","subject":"Science","chapter":"Electricity","section_title":"Ohm's Law & Circuits",
     "formula_name":"Electric Energy","expression":"E = P × t = VIt",
     "explanation":"Energy in joules or kWh","example":"P=100W,t=2h → E=200Wh=0.2kWh","display_order":9},
]


def seed():
    print(f"Seeding {len(FORMULAS)} formula entries...")
    # Check existing count
    try:
        existing = admin_client.table("formula_sheets").select("id", count="exact").execute()
        existing_count = existing.count or 0
        if existing_count > 0:
            print(f"Table already has {existing_count} rows. Skipping seed (already seeded).")
            print("To re-seed, delete existing rows first: DELETE FROM formula_sheets;")
            return
    except Exception as e:
        print(f"Warning: could not check existing rows: {e}")
        print("Proceeding with seed...")

    # Insert in batches of 20
    batch_size = 20
    inserted = 0
    for i in range(0, len(FORMULAS), batch_size):
        batch = FORMULAS[i:i+batch_size]
        result = admin_client.table("formula_sheets").insert(batch).execute()
        inserted += len(result.data or [])
        print(f"  Inserted batch {i//batch_size + 1}: {len(result.data or [])} rows")

    print(f"Done. Total inserted: {inserted}")


if __name__ == "__main__":
    seed()
