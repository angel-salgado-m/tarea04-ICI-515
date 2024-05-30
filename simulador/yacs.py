#!/usr/bin/env python3

import simpy
import argparse
import numpy as np
import string
class Debug(object):
    @classmethod
    def log(self, env: simpy.Environment, msg: str):
        print(f"{env.now:5.4f}:\t{msg}")


class Parametros(object):
    
    def __init__(self):
        self.procesos: None
        self.cores: None
        self.memoriaL1: None
        self.memoriaL2: None
        self.parsear_argumentos()

    @staticmethod
    def validar_procesos(valor):
        procesos = int(valor)
        if procesos < 1:
            raise argparse.ArgumentTypeError(f"{procesos} es un número inválido de procesos. Debe estar entre 1 y 100.")
        return procesos
    
    @staticmethod
    def validar_cores(valor):
        cores = int(valor)
        if cores < 1 or cores > 64 or cores % 2 != 0:
            raise argparse.ArgumentTypeError(f"{cores} es un número inválido de cores. i.e. : [1, 2, 4, 8, ..., 64].")
        return cores
    
    @staticmethod
    def validar_memoria(valor):
        memoria = int(valor)
        if memoria < 1 or memoria > 25:
            raise argparse.ArgumentTypeError(f"{memoria} es un número inválido de memoria. Debe estar entre 1 y 25.")
        return memoria


    def parsear_argumentos(self):
        parser = argparse.ArgumentParser(description="Simulador de un procesador\n")
        
        parser.add_argument("--procesos", required=True, type=self.validar_procesos, help="numero de procesos a simular\n")
        parser.add_argument("--cores", required=True, type=self.validar_cores, help="numero de cores\n")
        parser.add_argument("--L1", required=True, type=self.validar_memoria, help="cantidad de memoria L1\n")
        parser.add_argument("--L2", required=True, type=self.validar_memoria, help="cantidad de memoria L2\n")

        args = parser.parse_args()

        self.procesos = args.procesos
        self.cores = args.cores
        try:
            if args.L1 >= args.L2:
                raise argparse.ArgumentTypeError(f"La memoria L1 debe ser menor a la memoria L2")
            else:
                self.memoriaL1 = args.L1
                self.memoriaL2 = args.L2
        except argparse.ArgumentTypeError as e:
            print(e)
            exit(1)
        return self

class Proceso(object):
    def __init__(self, env: simpy.Environment, idProceso: int):
        self.env = env
        self.idProceso = idProceso
        self.num_datos= np.random.randint(1, 25)
        self.datos= [
            [letra,False] for letra in np.random.choice(list(string.ascii_lowercase), self.num_datos, replace=False)]

class Core(object):
    def __init__(self, idProceso:int, L1:int, L2:int):
        self.idProceso = idProceso
        self.L1 = L1
        self.L2 = L2
        self.procesosL1=[]
        self.procesosL2=[]
        self.Tcore=[]
        self.Tused=0
        self.prcsSolved=0
        self.cL1=0
        self.cL2=0
        self.ram=0
        self.TL1 = 4
        self.TL2 = 10
        self.inUse = False

class Procesador(object):

    def __init__(self, env: simpy.Environment, procesos: int, cores: int, memoriaL1: int, memoriaL2: int):
        self.env = env
        self.procesos = procesos
        self.cores = cores
        self.memoriaL1 = memoriaL1
        self.memoriaL2 = memoriaL2

        procesadorSim = self.env.process(self.run())

    def run(self):
        for idProceso in range(self.procesos):
            self.env.process(Proceso(idProceso))

    def use_data(self,core:Core,data):
        if len(core.procesosL1)>core.L1:
            core.procesosL1.pop(0)
        if len(core.procesosL2)>core.L2:
            core.procesosL2.pop(0)
        if data in core.procesosL1:
            core.cL1+=1
            yield core.TL1
        elif data in core.procesosL2:
            core.cL2+=1
            yield core.TL2 + core.TL1
        else:
            core.procesosL2.append(data)
            core.procesosL1.append(data)
            core.ram+=1
            yield core.TL2 + core.TL1 + core.ram

    def assign(self):
        for i in self.cores:
            if not i.inUse:
                i.inUse=True
                return i

    def succes(self,core:Core):
        core.inUse=False

class PC(object):
    def __init__(self, env: simpy.Environment, cores:int, L1:int, L2:int, procesos:int):
        self.env = env
        self.procesos=procesos
        self.Psuccess=0
        self.ram=200
        self.freecore=simpy.Container(env,cores,init=cores)
        self.cores=[Core(i,L1,L2) for i in range(cores)]
        self.env.process(self.run())

    

def main():

    parametros = Parametros()

    print(f"Procesos: {parametros.procesos} \n")
    print(f"Cores: {parametros.cores} \n")
    print(f"Memoria L1: {parametros.memoriaL1} \n")
    print(f"Memoria L2: {parametros.memoriaL2} \n")


    env = simpy.Environment()
    env.run()



if __name__ == "__main__":
    main()