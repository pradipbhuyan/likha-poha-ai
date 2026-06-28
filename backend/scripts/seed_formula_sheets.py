#!/usr/bin/env python3
"""
seed_formula_sheets.py -- Seed CBSE formula sheets Grade 5-10
Run: cd backend && .venv/bin/python scripts/seed_formula_sheets.py
Idempotent: skips if rows already exist.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services.auth_service import admin_client  # noqa: E402

FORMULAS = [
    # Grade 5 Maths
    {"grade": "Grade 5", "subject": "Mathematics", "chapter": "Shapes", "section_title": "Area and Perimeter", "formula_name": "Perimeter of Rectangle", "expression": "P = 2 x (l + b)", "explanation": "l=length, b=breadth", "example": "l=5,b=3 -> P=16", "display_order": 1},
    {"grade": "Grade 5", "subject": "Mathematics", "chapter": "Shapes", "section_title": "Area and Perimeter", "formula_name": "Area of Rectangle", "expression": "A = l x b", "explanation": "Multiply length by breadth", "example": "l=5,b=3 -> A=15", "display_order": 2},
    {"grade": "Grade 5", "subject": "Mathematics", "chapter": "Shapes", "section_title": "Area and Perimeter", "formula_name": "Perimeter of Square", "expression": "P = 4 x a", "explanation": "a=side length", "example": "a=4 -> P=16", "display_order": 3},
    {"grade": "Grade 5", "subject": "Mathematics", "chapter": "Shapes", "section_title": "Area and Perimeter", "formula_name": "Area of Square", "expression": "A = a^2", "explanation": "Square of side length", "example": "a=4 -> A=16", "display_order": 4},
    # Grade 6 Maths
    {"grade": "Grade 6", "subject": "Mathematics", "chapter": "Mensuration", "section_title": "Perimeter and Area", "formula_name": "Perimeter of Triangle", "expression": "P = a + b + c", "explanation": "Sum of all three sides", "example": "a=3,b=4,c=5 -> P=12", "display_order": 1},
    {"grade": "Grade 6", "subject": "Mathematics", "chapter": "Mensuration", "section_title": "Perimeter and Area", "formula_name": "Area of Triangle", "expression": "A = (1/2) x b x h", "explanation": "b=base, h=height", "example": "b=6,h=4 -> A=12", "display_order": 2},
    {"grade": "Grade 6", "subject": "Mathematics", "chapter": "Algebra", "section_title": "Basic Algebra", "formula_name": "Simple Interest", "expression": "SI = (P x R x T) / 100", "explanation": "P=principal, R=rate%, T=time years", "example": "P=1000,R=5,T=2 -> SI=100", "display_order": 3},
    # Grade 7 Maths
    {"grade": "Grade 7", "subject": "Mathematics", "chapter": "Triangles", "section_title": "Triangle Properties", "formula_name": "Pythagoras Theorem", "expression": "a^2 + b^2 = c^2", "explanation": "In right triangle, c=hypotenuse", "example": "a=3,b=4 -> c=5", "display_order": 1},
    {"grade": "Grade 7", "subject": "Mathematics", "chapter": "Mensuration", "section_title": "Circles", "formula_name": "Area of Circle", "expression": "A = pi x r^2", "explanation": "r=radius, pi~3.14159", "example": "r=7 -> A=154", "display_order": 2},
    {"grade": "Grade 7", "subject": "Mathematics", "chapter": "Mensuration", "section_title": "Circles", "formula_name": "Circumference of Circle", "expression": "C = 2 x pi x r", "explanation": "r=radius", "example": "r=7 -> C=44", "display_order": 3},
    {"grade": "Grade 7", "subject": "Mathematics", "chapter": "Ratio and Proportion", "section_title": "Proportion", "formula_name": "Percentage", "expression": "% = (Part / Whole) x 100", "explanation": "Convert fraction to percentage", "example": "25/50 x 100 = 50%", "display_order": 4},
    # Grade 8 Maths
    {"grade": "Grade 8", "subject": "Mathematics", "chapter": "Mensuration", "section_title": "3D Solids", "formula_name": "Volume of Cuboid", "expression": "V = l x b x h", "explanation": "l=length, b=breadth, h=height", "example": "l=3,b=4,h=5 -> V=60", "display_order": 1},
    {"grade": "Grade 8", "subject": "Mathematics", "chapter": "Mensuration", "section_title": "3D Solids", "formula_name": "Surface Area of Cuboid", "expression": "SA = 2(lb + bh + hl)", "explanation": "Sum of areas of all 6 faces", "example": "l=3,b=4,h=5 -> SA=94", "display_order": 2},
    {"grade": "Grade 8", "subject": "Mathematics", "chapter": "Mensuration", "section_title": "3D Solids", "formula_name": "Volume of Cylinder", "expression": "V = pi x r^2 x h", "explanation": "r=radius, h=height", "example": "r=7,h=10 -> V=1540", "display_order": 3},
    {"grade": "Grade 8", "subject": "Mathematics", "chapter": "Algebra", "section_title": "Algebraic Identities", "formula_name": "(a+b)^2", "expression": "(a+b)^2 = a^2 + 2ab + b^2", "explanation": "Square of sum", "example": "(x+3)^2 = x^2+6x+9", "display_order": 4},
    {"grade": "Grade 8", "subject": "Mathematics", "chapter": "Algebra", "section_title": "Algebraic Identities", "formula_name": "(a-b)^2", "expression": "(a-b)^2 = a^2 - 2ab + b^2", "explanation": "Square of difference", "example": "(x-3)^2 = x^2-6x+9", "display_order": 5},
    {"grade": "Grade 8", "subject": "Mathematics", "chapter": "Algebra", "section_title": "Algebraic Identities", "formula_name": "(a+b)(a-b)", "expression": "(a+b)(a-b) = a^2 - b^2", "explanation": "Difference of squares", "example": "(x+3)(x-3) = x^2-9", "display_order": 6},
    # Grade 9 Maths
    {"grade": "Grade 9", "subject": "Mathematics", "chapter": "Triangles", "section_title": "Area Formulas", "formula_name": "Heron's Formula", "expression": "A = sqrt[s(s-a)(s-b)(s-c)]", "explanation": "s=(a+b+c)/2 is semi-perimeter", "example": "a=3,b=4,c=5: s=6 -> A=6", "display_order": 1},
    {"grade": "Grade 9", "subject": "Mathematics", "chapter": "Circles", "section_title": "Circle Formulas", "formula_name": "Area of Circle", "expression": "A = pi x r^2", "explanation": "r=radius", "example": "r=14 -> A=616", "display_order": 2},
    {"grade": "Grade 9", "subject": "Mathematics", "chapter": "Circles", "section_title": "Circle Formulas", "formula_name": "Arc Length", "expression": "l = (theta/360) x 2 x pi x r", "explanation": "theta=central angle in degrees", "example": "theta=90,r=7 -> l=11", "display_order": 3},
    {"grade": "Grade 9", "subject": "Mathematics", "chapter": "Statistics", "section_title": "Central Tendency", "formula_name": "Mean", "expression": "x_bar = Sum(x) / n", "explanation": "Sum of observations divided by count", "example": "[2,4,6]: mean=4", "display_order": 4},
    {"grade": "Grade 9", "subject": "Mathematics", "chapter": "Probability", "section_title": "Probability", "formula_name": "Probability", "expression": "P(E) = n(E) / n(S)", "explanation": "n(E)=favourable, n(S)=total outcomes", "example": "P(Head)=1/2", "display_order": 5},
    {"grade": "Grade 9", "subject": "Mathematics", "chapter": "Coordinate Geometry", "section_title": "Distance and Midpoint", "formula_name": "Distance Formula", "expression": "d = sqrt[(x2-x1)^2 + (y2-y1)^2]", "explanation": "Distance between two points", "example": "(0,0) to (3,4): d=5", "display_order": 6},
    {"grade": "Grade 9", "subject": "Mathematics", "chapter": "Coordinate Geometry", "section_title": "Distance and Midpoint", "formula_name": "Midpoint Formula", "expression": "M = ((x1+x2)/2, (y1+y2)/2)", "explanation": "Midpoint of a line segment", "example": "(0,0)&(4,6) -> M=(2,3)", "display_order": 7},
    # Grade 9 Science
    {"grade": "Grade 9", "subject": "Science", "chapter": "Motion", "section_title": "Equations of Motion", "formula_name": "First Equation of Motion", "expression": "v = u + at", "explanation": "v=final vel, u=initial vel, a=accel, t=time", "example": "u=0,a=10,t=5 -> v=50", "display_order": 1},
    {"grade": "Grade 9", "subject": "Science", "chapter": "Motion", "section_title": "Equations of Motion", "formula_name": "Second Equation of Motion", "expression": "s = ut + (1/2)at^2", "explanation": "s=displacement", "example": "u=0,a=10,t=3 -> s=45", "display_order": 2},
    {"grade": "Grade 9", "subject": "Science", "chapter": "Motion", "section_title": "Equations of Motion", "formula_name": "Third Equation of Motion", "expression": "v^2 = u^2 + 2as", "explanation": "Relates velocity, accel, displacement", "example": "u=0,a=10,s=20 -> v=20", "display_order": 3},
    {"grade": "Grade 9", "subject": "Science", "chapter": "Force", "section_title": "Newton Laws", "formula_name": "Newton Second Law", "expression": "F = m x a", "explanation": "F=force(N), m=mass(kg), a=accel(m/s2)", "example": "m=5kg,a=3 -> F=15N", "display_order": 4},
    {"grade": "Grade 9", "subject": "Science", "chapter": "Force", "section_title": "Newton Laws", "formula_name": "Momentum", "expression": "p = m x v", "explanation": "p=momentum (kg m/s)", "example": "m=2kg,v=5 -> p=10", "display_order": 5},
    {"grade": "Grade 9", "subject": "Science", "chapter": "Work and Energy", "section_title": "Work Energy Power", "formula_name": "Work Done", "expression": "W = F x d x cos(theta)", "explanation": "F=force, d=displacement, theta=angle", "example": "F=10N,d=5m,theta=0 -> W=50J", "display_order": 6},
    {"grade": "Grade 9", "subject": "Science", "chapter": "Work and Energy", "section_title": "Work Energy Power", "formula_name": "Kinetic Energy", "expression": "KE = (1/2) x m x v^2", "explanation": "m=mass, v=velocity", "example": "m=2kg,v=4 -> KE=16J", "display_order": 7},
    {"grade": "Grade 9", "subject": "Science", "chapter": "Work and Energy", "section_title": "Work Energy Power", "formula_name": "Potential Energy", "expression": "PE = m x g x h", "explanation": "m=mass, g=9.8, h=height", "example": "m=2,h=5 -> PE=98J", "display_order": 8},
    {"grade": "Grade 9", "subject": "Science", "chapter": "Work and Energy", "section_title": "Work Energy Power", "formula_name": "Power", "expression": "P = W / t", "explanation": "P=power(W), W=work(J), t=time(s)", "example": "W=100J,t=5s -> P=20W", "display_order": 9},
    {"grade": "Grade 9", "subject": "Science", "chapter": "Gravitation", "section_title": "Gravity", "formula_name": "Universal Gravitation", "expression": "F = G x m1 x m2 / r^2", "explanation": "G=6.674e-11, r=distance between centres", "example": "Gravitational force between two masses", "display_order": 10},
    # Grade 10 Maths
    {"grade": "Grade 10", "subject": "Mathematics", "chapter": "Quadratic Equations", "section_title": "Quadratic Formula", "formula_name": "Quadratic Formula", "expression": "x = [-b +/- sqrt(b^2-4ac)] / 2a", "explanation": "For ax^2+bx+c=0", "example": "x^2-5x+6=0 -> x=3,2", "display_order": 1},
    {"grade": "Grade 10", "subject": "Mathematics", "chapter": "Quadratic Equations", "section_title": "Quadratic Formula", "formula_name": "Discriminant", "expression": "D = b^2 - 4ac", "explanation": "D>0:2 roots; D=0:1 root; D<0:no real", "example": "b^2-4ac=0 -> equal roots", "display_order": 2},
    {"grade": "Grade 10", "subject": "Mathematics", "chapter": "Arithmetic Progression", "section_title": "AP Formulas", "formula_name": "nth Term of AP", "expression": "a_n = a + (n-1)d", "explanation": "a=first term, d=common difference", "example": "a=2,d=3,n=5 -> a5=14", "display_order": 3},
    {"grade": "Grade 10", "subject": "Mathematics", "chapter": "Arithmetic Progression", "section_title": "AP Formulas", "formula_name": "Sum of n Terms of AP", "expression": "S_n = (n/2)[2a + (
