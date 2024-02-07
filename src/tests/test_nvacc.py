from src.dt4acc.command import update


def test_update_simple():
    update(element_id='Q1M1D1R', property_name='dx', value=0.5e-3)


def test_update_quad_strength():
    update(element_id='Q1M1D1R', property_name='main_multipole_strength', value=1.2)


def test_update_horizontal_steerer():
    update(element_id='Q1M1D1R', property_name='main_multipole_strength', value=1.2)
