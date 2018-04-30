import re
import time
import datetime
import logging
import collections


class ExchangeRateError(Exception):
    """Specific error for Exchange rate class"""
    pass

class ExchangeOpimiser(object):

    # Flag to update the rate table for all pair prices,
    # This is a class parameter to be shared by all instances of this class
    RATE_TABLE_NEEDED_UPDATED = True

    def __init__(self, name, log=None):

        if log is None:
            self._log = logging.getLogger('ExchangeOpimiser')

        self._name = name

        # This is a list to keep all registered currency and its exchange in the system
        # The format of each element is a string of "exchange_currency", e.g
        # ["KRAKEN_BTC", "KRAKEN_USD", "GDAX_BTC)", "GDAX_USD)", ...]
        # Any new currency id needs to be registered in this list
        # @TODO: this ideallt shall be kept in a DB or redis system
        self._all_currences_ids = []

        # This is a mappting to keep all exchange rates beween the currency/excange,
        # 
        # To avoid keeping looping to tiself, it is forbidden to exchange the same currency
        # at the same exchange so 0 is set as the price for the same currency at the same 
        # excahnge.
        #
        # E.g.,
        # {"KRAKEN_BTC" : {
        #       "KRAKEN_RGR" : [2.0, 2017-11-01T09:42:23+00:00],
        #       "KRAKEN_USD" : [1.1, 2017-11-01T09:42:23+00:00],
        #       "GDAX_BTC":    [1.0, 2017-11-01T09:42:23+00:00],
        #       ...
        #       },
        #   "KRAKEN_USD" : {
        #       "KRAKEN_BTC" : [0.9, 2017-11-01T09:42:23+00:00],
        #       "KRAKEN_RMB" : [7.6, 2017-11-01T09:42:23+00:00],
        #       "GDAX_USD":    [1.0, 2017-11-01T09:42:23+00:00],
        #       ...
        #       },
        #   ...
        # }
        # @TODO: this mapping ideally should be keep in a DB or Redis to 
        #        preventing data lossing when this module is off.
        self._all_price = {}
        
        # a lookup table of rates between any registered pair currency/exhange
        self._all_rates = None
        # a lookup table for any pair of price vertics
        self._next_vertices = None

    def _verify_price_update_request(self, request):
        """ Verify if the input price update request is valid

        :param request:  information for this price update request

        :return: True if the request is valid othrerwise False

        Note: a price update request shall be in following fomrat:

            <timestamp> <exchange> <source_currency> <destination_currency> <forward_factor>
            <backward_factor>
        """
        _info = request.split(" ")

        if (type(_info[0]) is str and
            type(_info[1]) is str and
            type(_info[2]) is str and
            type(_info[3]) is str and
            type(float(_info[4])) is float and
            type(float(_info[5])) is float):
            return True
        else:
            return False

    def price_update(self, request):
        """ update an price in the mapping dictionary 
        
        :param request:  information for this price update

        :raise:   ExchangeRateError if price update failed

        Note: a price update request shall be in following fomrat:

            <timestamp> <exchange> <source_currency> <destination_currency> <forward_factor>
            <backward_factor>

        """
        if not self._verify_price_update_request(request):
            print("Price update command :  {0} : not valid.".format(request))
            return

        _time, _exchange, _src_currency, _dest_currency, _forward, _backward = request.split(" ")
        _forward = float(_forward)
        _backward = float(_backward)

        _src_id = "{0}_{1}".format(_exchange, _src_currency)
        if _src_id not in self._all_currences_ids:
            # source currency id yet to registered
            self._add_new_currency_id(_src_id, _time)
            ExchangeOpimiser.RATE_TABLE_NEEDED_UPDATED = True

        _dest_id = "{0}_{1}".format(_exchange, _dest_currency)
        if _dest_id not in self._all_currences_ids:
            # dest currency id yet to registered
            self._add_new_currency_id(_dest_id, _time)
            ExchangeOpimiser.RATE_TABLE_NEEDED_UPDATED = True

        if _dest_id not in self._all_price[_src_id]:
            # no exising rate between the source and destination currencies
            self._all_price[_src_id][_dest_id] = [_forward, _time]
            self._all_price[_dest_id][_src_id] = [_backward, _time]
            ExchangeOpimiser.RATE_TABLE_NEEDED_UPDATED = True
        else:
            # rate between the two exists then check the time stamp
            time_format='%Y-%m-%dT%H:%M:%S%z'

            # time stamp for the existing rate
            _existing_time = self._all_price[_src_id][_dest_id][1]
            #convert time format '2017-11-01T09:42:23+00:40' to "'2017-11-01T09:42:23+0040'"
            _existing_time = re.sub(r'(?<=[+=][0-9]{2}):', '', _existing_time)
            # get unix time
            _existing_time_stamp = time.mktime(time.strptime(_existing_time, time_format))

            #convert time format '2017-11-01T09:42:23+00:40' to "'2017-11-01T09:42:23+0040'"
            _t_time = re.sub(r'(?<=[+=][0-9]{2}):', '', _time)
            # time stamp in the price request
            _new_time_stamp = time.mktime(time.strptime(_t_time, time_format))

            if _existing_time_stamp > _new_time_stamp:
                # the existing rate is newer than the request one, so do nothing here
                pass
            else:
                # the existing rate is older than the request one, so update it
                self._all_price[_src_id][_dest_id] = [_forward, _time]
                self._all_price[_dest_id][_src_id] = [_backward, _time]
                ExchangeOpimiser.RATE_TABLE_NEEDED_UPDATED = True


    def _add_new_currency_id(self, exchange_currency, time_added):
        """ adding a non-existing currency id to the current system 
        
        :param exchange_currency: new excange and currency identification
        :param time_added: timeflame to this addition

        :raise:   ExchangeRateError if adding a new exchange/currency failed
        """
        try:
            assert exchange_currency not in self._all_currences_ids

            # update rate mapping table
            self._all_price[exchange_currency] = {}

            _exchange, _currency = exchange_currency.split("_")
            for item in self._all_currences_ids:
                if item.split("_")[1] == _currency:
                    self._all_price[item][exchange_currency] = [1.0, time_added]
                    self._all_price[exchange_currency][item] = [1.0, time_added]

            # append to currency list
            self._all_currences_ids.append(exchange_currency)
        except Exception:
            _msg = "Error occured in adding new currency {0}".format(exchange_currency)
            print(_msg)
            raise ExchangeRateError(_msg)


    def _find_path(self, src_id, dest_id):
        """ find the best rate path in the requeted format 
        
        :param src_id: soruce curreny id, e.g "KRAKEN_BTC"
        :param dest_id: distination curreny id, e.g "KRAKENUSD"

        :return:   Path list between the two ids
        
        """
        path = []
        if self._next_vertices[src_id][dest_id] is None:
            # no path found
            pass
        else:
            # starting point
            path.append(src_id)

            next = src_id
            while next != dest_id:
                next = self._next_vertices[next][dest_id]
                path.append(next)
               
        return path

    def _print_path(self, b_path):
        """ print the best rate path in the requeted format 
        
        :param b_path: path list to print out
        """
        print()
        print(b_path[0])
        for itr in range(1, len(b_path)):
            # convert currency id to the requitred output format
            # e.g. "KRAKEN_BTC" --> "KRAKEN, BTC"
            print(b_path[itr].replace("_", ", "))
        print("BEST_RATES_END")
        print()

    def _latest_rate_table(self):
        """ update the latest rate table beween any two currency/excahnge """
        # constrcut an empty OrderedDict object for the rate table 
        self._all_rates = collections.OrderedDict()
        # constrcut an empty OrderedDict object for the vertex table
        self._next_vertices = collections.OrderedDict()

        for itm_row in self._all_currences_ids:
            self._all_rates[itm_row] = collections.OrderedDict()
            self._next_vertices[itm_row] = collections.OrderedDict()
            for itm_col in self._all_currences_ids:
                if itm_col in self._all_price[itm_row]:
                    # price exists between the pair
                    # update rate table
                    self._all_rates[itm_row][itm_col] = self._all_price[itm_row][itm_col][0]
                    # update vertex table
                    self._next_vertices[itm_row][itm_col] = itm_col
                else:
                    # price not exists between the pair
                    # update rate table
                    self._all_rates[itm_row][itm_col] = 0
                    # update vertex table
                    self._next_vertices[itm_row][itm_col] = None

        # reset the flag 
        ExchangeOpimiser.RATE_TABLE_NEEDED_UPDATED = False

    def _verify_best_price_request(self, _head_str, _src_exchange, _src_currency, _dest_exchange, _dest_currency):
        """ verify best rate request command 
        
        :param _head_str : head string of the request
        :param _src_exchange: source exchange string id
        :param _src_currency: source currency string id
        :param _dest_exchange: destination exchange string id
        :param _dest_currency: destination currency string id

        :return: True if passing the verification otherwies False

        """

        if (_head_str == "EXCHANGE_RATE_REQUEST" and
            type(_src_exchange) is str and
            type(_src_currency) is str and
            type(_dest_exchange) is str and
            type(_dest_currency) is str):
            return True
        else:
            return False

    def best_rate(self, request):
        """ Finding the best price for the specified source and destination currencies

        :param request: exchange rate request string
        
        :raise:   ExchangeRateError if finding a nest rate failed

        Note: the best rate requst shall be in following format

            EXCHANGE_RATE_REQUEST <source_exchange> <source_currency> <destination_exchange>
            <destination_currency>

        """
        # path list
        out_list = []
        # best price
        _rate = None
        
        try:
            _head_str, _src_exchange, _src_currency, _dest_exchange, _dest_currency = request.split(" ")

            # verify request command
            if not self._verify_best_price_request(_head_str, _src_exchange, _src_currency, 
                _dest_exchange, _dest_currency):
                # added error message to print out
                out_list.append("Best Rate request : {0} : is invalid".format(request))
            else:
                _src_id = "{0}_{1}".format(_src_exchange, _src_currency)
                _dest_id = "{0}_{1}".format(_dest_exchange, _dest_currency)

                if _src_id in self._all_currences_ids and _dest_id in self._all_currences_ids:
                    # both currencies ids have been registered in the system

                    # generate latest rate table and price vertex table
                    if ExchangeOpimiser.RATE_TABLE_NEEDED_UPDATED:
                        self._latest_rate_table()

                    # modified Floyd-Warshall algorithm 
                    for itm_mid in self._all_currences_ids:
                        for itm_row in self._all_currences_ids:
                            for itm_col in self._all_currences_ids:
                                _val = self._all_rates[itm_row][itm_mid] * self._all_rates[itm_mid][itm_col]
                                if self._all_rates[itm_row][itm_col] < _val:
                                    self._all_rates[itm_row][itm_col] = _val
                                    self._next_vertices[itm_row][itm_col] = self._next_vertices[itm_row][itm_mid]

                    # obtain the best rate
                    _rate = self._all_rates[_src_id][_dest_id]
                    # obtain path list
                    out_list = self._find_path(_src_id, _dest_id)
                else:
                    if _src_id not in self._all_currences_ids:
                        err_msg = "Error: source currency id {0}_{1} yet registered in system".format(_src_exchange, _src_currency)
                        out_list.append(err_msg)

                    if _dest_id not in self._all_currences_ids:
                        err_msg = "Error: destination currency id {0}_{1} yet registered in system".format(_dest_exchange, _dest_currency)
                        out_list.append(err_msg)
        except Exception as e:
            _msg = "Error occured in calculating the best price: {0}".format(str(e))
            print(_msg)
            raise ExchangeRateError(_msg)
        
        # insert head message to print out
        start_msg = "BEST_RATES_BEGIN {0} {1} {2} {3} {4}".format(_src_exchange, _src_currency,
                    _dest_exchange, _dest_currency, _rate)
        out_list.insert(0, start_msg)
        
        # print out
        self._print_path(out_list)
            

def demo():
    
    p1 = ExchangeOpimiser("Sydney Exchange")
    s1 = '2017-11-01T09:42:23+00:00 KRAKEN BTC USD 1000.0 0.0009'
    p1.price_update(s1)
    s2 = '2017-11-01T09:43:23+00:00 GDAX BTC USD 1001.0 0.0008'
    p1.price_update(s2)

    r1 = "EXCHANGE_RATE_REQUEST KRAKEN BTC GDAX USD"
    p1.best_rate(r1)
    r2 = "EXCHANGE_RATE_REQUEST KRAKEN USD GDAX BTC"
    p1.best_rate(r2)
    r3 = "EXCHANGE_RATE_REQUEST GDAX USD KRAKEN BTC"
    p1.best_rate(r3)
    r4 = "EXCHANGE_RATE_REQUEST GDAX BTC KRAKEN USD"
    p1.best_rate(r4)
    r5 = "EXCHANGE_RATE_REQUEST GDAX BTC KRAKEN RMB"
    p1.best_rate(r5)

    while(True):
       
        request = input("Input Request :  ")
        if request.startswith("exit"):
            break
        elif request.startswith("EXCHANGE_RATE_REQUEST"):
            p1.best_rate(request)
        else:
            try:
                _time = request.split(" ")[0]
                _time = re.sub(r'(?<=[+=][0-9]{2}):', '', _time)
                
                time_format='%Y-%m-%dT%H:%M:%S%z'
                datetime.datetime.strptime(_time, time_format)
                p1.price_update(request)
                print()
            except Exception:
                print("Invalid input : {0}".format(request))
                print()
                continue
    
    print("program ends.")
