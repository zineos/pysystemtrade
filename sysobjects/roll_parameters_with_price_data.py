import datetime
from syscore.objects import missing_data
from sysobjects.rolls import contractDateWithRollParameters, rollParameters
from sysobjects.contracts import contractDate
from sysdata.futures.futures_per_contract_prices import dictFuturesContractFinalPrices
from sysobjects.contract_dates_and_expiries import listOfContractDateStr

HELD= "held"
PRICED= "priced"

class contractWithRollParametersAndPrices(object):
    """
    Including prices in our contract means we can navigate more accurately through roll cycles
    """

    def __init__(
            self,
            contract_with_roll_parameters: contractDateWithRollParameters,
            dict_of_final_price_data: dictFuturesContractFinalPrices):
        """

        :param contract_with_roll_parameters: contractWithRollParameters
        :param dict_of_final_price_data: object of type dictFuturesContractFinalPrices
        """

        self.contract = contract_with_roll_parameters
        self.prices = dict_of_final_price_data

    @property
    def date_str(self) ->str:
        return self.contract.date_str

    @property
    def desired_roll_date(self) -> datetime.datetime:
        return self.contract.desired_roll_date

    def next_held_contract(self):
        next_held_contract_with_roll_parameters = self.contract.next_held_contract()
        return contractWithRollParametersAndPrices(
            next_held_contract_with_roll_parameters, self.prices
        )

    def next_priced_contract(self):
        next_priced_contract_with_roll_parameters = self.contract.next_priced_contract()
        return contractWithRollParametersAndPrices(
            next_priced_contract_with_roll_parameters, self.prices
        )

    def previous_priced_contract(self):
        previous_priced_contract_with_roll_parameters = (
            self.contract.previous_priced_contract()
        )
        return contractWithRollParametersAndPrices(
            previous_priced_contract_with_roll_parameters, self.prices
        )

    def previous_held_contract(self):
        previous_held_contract_with_roll_parameters = (
            self.contract.previous_held_contract()
        )
        return contractWithRollParametersAndPrices(
            previous_held_contract_with_roll_parameters, self.prices
        )

    def find_next_held_contract_with_price_data(self):
        """
        Finds the first contract in list_of_contract_dates after current_contract, within the held roll cycle
           defined by roll parameters

        :return: a contract object with roll data, or None if we can't find one
        """
        next_contract = self._find_next_contract_with_price_data(HELD)

        return next_contract

    def find_next_priced_contract_with_price_data(self):
        """
        Finds the first contract in list_of_contract_dates after current_contract, within the priced roll cycle
           defined by roll parameters

        :return: a contract object with roll data, or None if we can't find one
        """

        next_contract = self._find_next_contract_with_price_data(PRICED)

        return next_contract

    def _find_next_contract_with_price_data(self, contract_type: str):
        """
        Finds the first contract in list_of_contract_dates after current_contract, within the priced roll cycle
           defined by roll parameters

        :return: a contract object with roll data, or None if we can't find one
        """
        assert contract_type in [HELD, PRICED]
        contract_attribute_str = "next_%s_contract" % contract_type

        try_contract = getattr(self, contract_attribute_str)()
        list_of_contract_dates = self.prices.sorted_contract_date_str()
        final_contract_date = list_of_contract_dates[-1]

        while try_contract.date_str <= final_contract_date:
            if try_contract.date_str in list_of_contract_dates:
                return try_contract
            try_contract = getattr(self, contract_attribute_str)()

        # Nothing found
        return missing_data


    def find_previous_priced_contract_with_price_data(self):
        """
        Finds the closest contract in list_of_contract_dates before current_contract, within the priced roll cycle
           defined by roll parameters

        :return: a contract object with roll data, or None if we can't find one
        """
        previous_contract = self._find_previous_contract_with_price_data(PRICED)

        return previous_contract

    def find_previous_held_contract_with_price_data(self):
        """
        Finds the closest contract in list_of_contract_dates before current_contract, within the held roll cycle
           defined by roll parameters

        :return: a contract object with roll data, or None if we can't find one
        """
        previous_contract = self._find_previous_contract_with_price_data(HELD)

        return previous_contract

    def _find_previous_contract_with_price_data(self, contract_type: str):
        """
        Finds the closest contract in list_of_contract_dates before current_contract, within the held roll cycle
           defined by roll parameters

        :return: a contract object with roll data, or None if we can't find one
        """
        assert contract_type in [HELD, PRICED]
        contract_attribute_str = "previous_%s_contract" % contract_type

        try_contract = getattr(self, contract_attribute_str)()
        list_of_contract_dates = self.prices.sorted_contract_date_str()
        first_contract_date = list_of_contract_dates[0]

        while try_contract.date_str >= first_contract_date:
            if try_contract.date_str in list_of_contract_dates:
                return try_contract
            try_contract = getattr(self, contract_attribute_str)()

        # Nothing found
        return missing_data


    def find_best_carry_contract_with_price_data(self):
        """
        Finds the best carry contract in list_of_contract_dates after current_contract, within the roll cycle
           defined by roll parameters

        This will either be the next valid contract, or the first valid preceeding contract in the price cycle

        :return: a contract object with roll data, or None if we can't find one
        """
        carry_offset = self.contract.roll_parameters.carry_offset

        if carry_offset == 1.0:
            best_carry_contract = self.find_next_priced_contract_with_price_data()
        elif carry_offset == -1.0:
            best_carry_contract = self.find_previous_priced_contract_with_price_data()
        else:
            raise Exception("Carry offset should be 1 or -1!")

        return best_carry_contract



def find_earliest_held_contract_with_price_data( roll_parameters_object: rollParameters,
                 price_dict: dictFuturesContractFinalPrices):
        """
        Find the earliest contract we can hold in a given list of contract dates
        To hold the contract, it needs to be in the held roll cycle and the list_of_contract_dates
        And it's carry contract needs to be in the priced roll cycle and the list_of_contract_dates

        :return: contract with roll parameters, or None
        """
        list_of_contract_dates = price_dict.sorted_contract_date_str()

        earliest_contract = find_earliest_held_contract_with_data(list_of_contract_dates, roll_parameters_object,
                                                                  price_dict)

        return earliest_contract

def find_earliest_held_contract_with_data(list_of_contract_dates: listOfContractDateStr,
                                          roll_parameters_object: rollParameters,
                                          price_dict: dictFuturesContractFinalPrices) \
        -> contractDateWithRollParameters:
    try_contract = initial_contract_to_try_with(list_of_contract_dates, roll_parameters_object, price_dict)
    final_contract_date = list_of_contract_dates[-1]

    while try_contract.date_str <= final_contract_date:
        is_contract_ok = check_valid_contract(try_contract, list_of_contract_dates)
        # Okay this works
        if is_contract_ok:
            contract_to_return = try_contract.contract
            return contract_to_return

        # okay it's not suitable
        # Let's try another one
        try_contract = try_contract.find_next_held_contract_with_price_data()

    # Nothing found
    return missing_data


def initial_contract_to_try_with(list_of_contract_dates: list,
                                 roll_parameters_object: rollParameters,
                                 price_dict: dictFuturesContractFinalPrices):

    plausible_earliest_contract_date = list_of_contract_dates[0]
    plausible_earliest_contract = contractDateWithRollParameters(
        contractDate(plausible_earliest_contract_date), roll_parameters_object
    )

    try_contract = contractWithRollParametersAndPrices(
        plausible_earliest_contract, price_dict
    )

    return try_contract

def check_valid_contract(try_contract: contractWithRollParametersAndPrices,
                         list_of_contract_dates: listOfContractDateStr):

    if try_contract.date_str in list_of_contract_dates:
        # possible candidate, let's check carry
        try_carry_contract = (
            try_contract.find_best_carry_contract_with_price_data()
        )

        ## No good
        if try_carry_contract is missing_data:
            return False

    ## All good
    return True
