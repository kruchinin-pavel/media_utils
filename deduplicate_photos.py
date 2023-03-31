import gc
import multiprocessing
import os
from time import sleep
from typing import List, Iterable


def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=printEnd)
    # Print New Line on Complete
    if iteration == total:
        print()


def _by_one(func, params: List):
    res = []
    for task in params:
        if isinstance(task, Iterable):
            res.append(func(*task))
        else:
            res.append(func(task))
    return res


def run_parallel3(func, tasks: List, by_one=True, workers=multiprocessing.cpu_count() - 1, prgrs=False):
    if workers > 0:
        with multiprocessing.Pool(workers) as pool:
            results = []
            batch_size = max(multiprocessing.cpu_count(), int(len(tasks) / multiprocessing.cpu_count()))
            while len(tasks) > 0:
                increment = min(batch_size, len(tasks))
                batch = tasks[:increment]
                del tasks[:increment]
                if by_one:
                    results.append(pool.apply_async(_by_one, args=(func, batch)))
                else:
                    results.append(pool.apply_async(func, args=([batch])))
            init_len = len(results)
            while len(results) > 0:
                if prgrs:
                    printProgressBar(init_len - len(results), init_len, 'prl')
                for idx, r in enumerate(results):
                    if r.ready():
                        if by_one:
                            for r in r.get():
                                yield r
                        else:
                            yield r.get()
                        del results[idx]
                        gc.collect()
                        break
                sleep(1)
    else:
        if by_one:
            for idx, task in enumerate(tasks):
                if prgrs:
                    printProgressBar(idx, len(tasks), 'prl')
                if isinstance(task, Iterable):
                    yield func(*task)
                else:
                    yield func(task)
        else:
            for r in enumerate(func(tasks)):
                yield r


# global total_saved
# total_saved = 0


def process_dir(r, files):
    total_saved = 0
    print(f'Scanning {r}')
    for name in [_f for _f in files if "~" == _f[-1]]:
        fname_dup = os.path.join(r, name)
        fname_org = os.path.join(r, name[:-1])
        if os.path.isfile(fname_org):
            sz_orig = os.stat(fname_org).st_size
            sz_dup = os.stat(fname_dup).st_size
            if sz_orig > 0 and sz_orig == sz_dup:
                total_saved += sz_orig
                print(f'{fname_dup}: {sz_orig / 1024 / 1024.}. Total saved {total_saved / 1024 / 1024.}mb'.replace('/',
                                                                                                                   '\\'))
                os.remove(fname_dup)
            else:
                print(f'Dup with dif size {fname_dup}: {sz_dup}!={sz_orig}'.replace('/', '\\'))
        else:
            print(f'recover {fname_dup} to {fname_org}'.replace('/', '\\'))
            os.rename(fname_dup, fname_org)
    return r


def dup(str):
    # dups = [s for s in files if '~' == s[-1]]
    # for l in os.walk(str, topdown=False):
    batch = 10
    params = []
    running = []
    for r, d, f in os.walk(str):
        params.append([r, f])
        print(f'read {len(params)} paths')
        if len(params) >= batch:
            for r in running:
                print(f'Done  {r}')
            running = run_parallel3(process_dir, params, workers=batch)
            params = []

    if len(params) > 0:
        print(f'read {len(params)} paths')
        for r in run_parallel3(process_dir, params, workers=batch):
            print(f'Done final  {r}')


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    try:
        # dup('//192.168.2.1/black_hdd/photo_bkp/'.replace('/', '\\'))
        dup('//192.168.2.1/photo_bkp/'.replace('/', '\\'))
    except Exception as ex:
        print(f'Error: {ex}')
