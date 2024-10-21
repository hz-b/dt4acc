from importlib.resources import files

conversion_factors_file = files(__name__).joinpath("../resources/conversion-factors-simplified-table.xlsx")
conversion_factors_file_tl = files(__name__).joinpath("../resources/conversion-factors-simplified-table-TL.xlsx")