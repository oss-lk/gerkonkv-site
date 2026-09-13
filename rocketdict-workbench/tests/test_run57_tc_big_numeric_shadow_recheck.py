from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.translation_rescue import evaluate_rescue_pair


CASES = [
    (
        1577,
        "This is the\nThickness of the Air at the darkest Part of the first dark Ring made by\nperpendicular Rays; and half this Thickness multiplied by the\nProgression, 1, 3, 5, 7, 9, 11, &c. gives the Thicknesses of the Air at\nthe most luminous Parts of all the brightest Rings, _viz._ ",
        "Это Толщина Воздуха в самой темной Части первого Темного Кольца, сделанная перпендикулярными Лучами; и половина этой Толщины, умноженная на Прогресс, 1, 3, 5, 7, 9, 11, &c. дает Толщину Воздуха в наиболее светящихся Частях всех самых ярких Колец, _viz._",
    ),
    (
        2288,
        "And therefore these differences will be 3/8A and 5/16A. Add\nthe first to 9A and subduct the last from 8A, and you will have the\nDiameters of the Circles made by the least and most refrangible Rays\n75/8A and ((61-1/2)/8)A. These diameters are therefore to one another as\n75 to 61-1/2 or 50 to 41, and ",
        "И поэтому эти различия будут 3/8A и 5/16A. Добавьте первое к 9A и вычтите последнее из 8A, и вы получите Диаметры Кругов, сделанные наименее и наиболее рефрагируемыми Лучами 75/8A и ((61-1/2)/8)A. Поэтому эти диаметры друг к другу равны 75 к 61-1/2 или 50 к 41, и",
    ),
    (
        2355,
        "And therefore, if the distance of the\nChart from the Concave-Surface of the Speculum be six Feet (as it was in\nthe third of these Observations) the Diameters of the Rings of this\nbright yellow Light upon the Chart shall be 1'688, 2'389, 2'925, 3'375\nInches: For these Diameters are to six Feet, as ",
        "И поэтому, если расстояние Карты от Вогнутой Поверхности Зеркала составляет шесть футов (как это было в третьем из этих Наблюдений), Диаметры Колец этого яркого желтого Света на Карте будут 1'688, 2'389, 2'925, 3'375 дюйма: Ибо эти Диаметры к шести футам, как",
    ),
]


def test_historical_exact_source_tc_big_rank0_candidates_pass_current_gates():
    for sequence, source, target in CASES:
        verdict = evaluate_rescue_pair(source, target)
        emphasis = compare_emphasis_markup_preservation(source, target)
        assert verdict["numeric_symbol"]["passed"] is True, (sequence, verdict)
        assert verdict["punctuation_passed"] is True, (sequence, verdict)
        assert verdict["length_passed"] is True, (sequence, verdict)
        assert verdict["strictly_eligible"] is True, (sequence, verdict)
        assert emphasis["passed"] is True, (sequence, emphasis)
