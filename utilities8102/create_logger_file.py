import logging

def setup_log(name):

    '''Create a log file name based on the name passed through

    name = the name of the log file we want to name it
    '''

    logger = logging.getLogger(name)   
    logger.setLevel(logging.DEBUG) 
    log_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    filename = f"./logs/{name}.log"
    log_handler = logging.FileHandler(filename)
    log_handler.setLevel(logging.DEBUG)
    log_handler.setFormatter(log_format)
    logger.addHandler(log_handler)
    return logger