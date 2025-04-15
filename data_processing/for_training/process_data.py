

from data_processing.for_training.processing_functions.calculate_elos import calculate_elos
from helpers.database_helpers.get_and_set_functions import get_all_matches



def process_data(conn):
    matches = get_all_matches(conn)

    calculate_elos(matches)