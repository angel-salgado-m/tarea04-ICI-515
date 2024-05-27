#!/usr/bin/env python3

import simpy
import argparse

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
            if args.L1 > args.L2:
                raise argparse.ArgumentTypeError(f"La memoria L1 debe ser menor a la memoria L2")
            else:
                self.memoriaL1 = args.L1
                self.memoriaL2 = args.L2
        except argparse.ArgumentTypeError as e:
            print(e)
            exit(1)
        return self
        

def main():

    parametros = Parametros()

    print(f"Procesos: {parametros.procesos} \n")
    print(f"Cores: {parametros.cores} \n")
    print(f"Memoria L1: {parametros.memoriaL1} \n")
    print(f"Memoria L2: {parametros.memoriaL2} \n")


    #env = simpy.Environment()
    #env.run()



if __name__ == "__main__":
    main()