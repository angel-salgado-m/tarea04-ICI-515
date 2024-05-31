import simpy
import argparse
import numpy as np
import string
import os
import time

Tram = 200 #ciclos de reloj, velocidad de acceso a datos en memoria, definida el enunciado

class Debug(object):
    @classmethod
    def log(cls, env: simpy.Environment, msg: str):
        print(f"{env.now:5.4f}:\t{msg}")

class Props(object):
    def __init__(self):
        self.procesos = None
        self.cores = None
        self.memoriaL1 = None
        self.memoriaL2 = None
        self.parsear_argumentos()

    @staticmethod
    def validar_procesos(valor):
        procesos = int(valor)
        if procesos < 1 :
            raise argparse.ArgumentTypeError(f"{procesos} es un número inválido de procesos. Debe ser mayor que 1")
        return procesos

    @staticmethod
    def validar_cores(valor):
        cores = int(valor)
        if cores < 1 or cores > 64 or cores % 2 != 0:
            raise argparse.ArgumentTypeError(f"{cores} es un número inválido de cores. Debe estar entre [1, 2, 4, 8, ..., 64].")
        return cores

    @staticmethod
    def validar_memoria(valor):
        memoria = int(valor)
        if memoria < 1 or memoria > 25:
            raise argparse.ArgumentTypeError(f"{memoria} es un número inválido de memoria. Debe estar entre 1 y 25.")
        return memoria

    def parsear_argumentos(self):
        parser = argparse.ArgumentParser(description="Simulador de un procesador\n")
        
        parser.add_argument("--procesos", required=True, type=self.validar_procesos, help="Número de procesos a simular\n")
        parser.add_argument("--cores", required=True, type=self.validar_cores, help="Número de cores\n")
        parser.add_argument("--L1", required=True, type=self.validar_memoria, help="Cantidad de memoria L1\n")
        parser.add_argument("--L2", required=True, type=self.validar_memoria, help="Cantidad de memoria L2\n")

        args = parser.parse_args()

        self.procesos = args.procesos
        self.cores = args.cores
        if args.L1 >= args.L2:
            raise argparse.ArgumentTypeError(f"La memoria L1 debe ser menor a la memoria L2")
        else:
            self.memoriaL1 = args.L1
            self.memoriaL2 = args.L2

class Proceso(object):
    def __init__(self, env: simpy.Environment, idProceso: int):
        self.env = env
        self.idProceso = idProceso
        self.num_datos = np.random.randint(1, 25)
        self.datos = [
            [letra, False] for letra in np.random.choice(list(string.ascii_lowercase), self.num_datos, replace=False)
        ]
        self.tespera = np.random.randint(1, 10)  # Simulación de t_espera
        self.tfinalizacion = np.random.randint(1, 10)  # Simulación de t_finalizacion

class Core(object):
    def __init__(self, idCore: int, L1: int, L2: int):
        self.idCore = idCore
        self.L1 = L1
        self.L2 = L2
        self.procesosL1 = []
        self.procesosL2 = []
        self.Tcore = []
        self.Tused = 0
        self.prcsSolved = 0
        self.cL1 = 0
        self.cL2 = 0
        self.ram = 0
        self.TL1 = 4
        self.TL2 = 10
        self.inUse = False


class SimularEquipo(object):
    def __init__(self, env: simpy.Environment, cores: int, L1: int, L2: int, procesos: int):
        self.env = env
        self.procesos = procesos
        self.Psuccess = 0
        self.ram = Tram
        self.total_service_time = 0
        self.throughput = 0
        self.freecore = simpy.Container(env, cores, init=cores)
        self.cores = [Core(i, L1, L2) for i in range(cores)]
        self.env.process(self.run())

    def run(self):
        for idProceso in range(self.procesos):
            self.env.process(self.crear_proceso(idProceso))
        yield self.env.timeout(0)

    def crear_proceso(self, idProceso: int):
        proceso = Proceso(self.env, idProceso)
        Debug.log(self.env, f"IdProceso:{idProceso} Datos:{proceso.num_datos}")
        yield self.env.timeout(0)  # Añadiendo una pausa para crear el proceso
        while True:
            core = self.assign()
            if core:
                start_time = self.env.now
                for data in proceso.datos:
                    yield self.env.process(self.use_data(core, data))
                end_time = self.env.now
                service_time = end_time - start_time
                self.total_service_time += service_time
                self.throughput += 1
                self.success(core)
                Debug.log(self.env, f"Proceso id:{idProceso} terminado. Tiempo de servicio: {service_time:.4f}")
                break
            else:
                Debug.log(self.env, f"Proceso id:{idProceso} no pudo ser asignado a ningún core.")
                break
        yield self.env.timeout(proceso.tfinalizacion)

    def use_data(self, core: Core, data):
        if len(core.procesosL1) > core.L1:
            core.procesosL1.pop(0)
        if len(core.procesosL2) > core.L2:
            core.procesosL2.pop(0)
        if data in core.procesosL1:
            core.cL1 += 1
            yield self.env.timeout(core.TL1)
        elif data in core.procesosL2:
            core.cL2 += 1
            yield self.env.timeout(core.TL2 + core.TL1)
        else:
            core.procesosL2.append(data)
            core.procesosL1.append(data)
            core.ram += 1
            yield self.env.timeout(core.TL2 + core.TL1 + 200)

    def assign(self):
        for core in self.cores:
            if not core.inUse:
                core.inUse = True
                return core
        return None
    
    def success(self, core: Core):
        core.inUse = False
    
    def resultados(self):
        avg_service_time = self.total_service_time / self.procesos if self.procesos > 0 else 0
        return self.throughput, avg_service_time
    
class Procesador(object):
    def __init__(self, env: simpy.Environment, procesos: int, cores: int, memoriaL1: int, memoriaL2: int):
        self.env = env
        self.procesos = procesos
        self.cores = [Core(i, memoriaL1, memoriaL2) for i in range(cores)]
        self.memoriaL1 = memoriaL1
        self.memoriaL2 = memoriaL2
        self.throughput = 0
        self.total_service_time = 0
        self.core_usage = np.zeros(cores).tolist()
        self.env.process(self.run())

    def run(self):
        for idProceso in range(self.procesos):
            self.env.process(self.crear_proceso(idProceso))
        yield self.env.timeout(0)

    def crear_proceso(self, idProceso: int):
        proceso = Proceso(self.env, idProceso)
        Debug.log(self.env, f"Proceso id:{idProceso} creado con {proceso.num_datos} datos.")
        yield self.env.timeout(proceso.tespera)
        while True:
            core = self.assign()
            if core:
                start_time = self.env.now
                for data in proceso.datos:
                    yield self.env.process(self.use_data(core, data))
                end_time = self.env.now
                service_time = end_time - start_time
                self.total_service_time += service_time
                self.core_usage[core.idCore] += service_time
                self.throughput += 1
                self.success(core)
                Debug.log(self.env, f"Proceso id:{idProceso} terminado. Tiempo de servicio: {service_time:.4f}")
                break
            else:
                Debug.log(self.env, f"Proceso id:{idProceso} no pudo ser asignado a ningún core.")
                break
        yield self.env.timeout(proceso.tfinalizacion)

    def use_data(self, core: Core, data):
        if len(core.procesosL1) > core.L1:
            core.procesosL1.pop(0)
        if len(core.procesosL2) > core.L2:
            core.procesosL2.pop(0)
        if data in core.procesosL1:
            core.cL1 += 1
            yield self.env.timeout(core.TL1)
        elif data in core.procesosL2:
            core.cL2 += 1
            yield self.env.timeout(core.TL2 + core.TL1)
        else:
            core.procesosL2.append(data)
            core.procesosL1.append(data)
            core.ram += 1
            yield self.env.timeout(core.TL2 + core.TL1 + 200)  # TRAM=200

    def assign(self):
        available_cores = [core for core in self.cores if not core.inUse]
        if available_cores:
            selected_core = available_cores[0]  # Select the first available core
            selected_core.inUse = True
            return selected_core
        return None

    def success(self, core: Core):
        core.inUse = False

    def resultados(self):
        avg_service_time = self.total_service_time / self.procesos if self.procesos > 0 else 0
        core_usage_percent = [round((usage / self.env.now * 100),4) for usage in self.core_usage]
        return self.throughput, avg_service_time, core_usage_percent


def main():
    start=time.time()
    os.system('cls' if os.name == 'nt' else 'clear')
    params = Props()

    print(f"Procesos: {params.procesos} ")
    print(f"Cores: {params.cores} ")
    print(f"Memoria L1: {params.memoriaL1} ")
    print(f"Memoria L2: {params.memoriaL2} ")
    print("="*100, "\n")

    env = simpy.Environment()
    procesador = Procesador(env, params.procesos, params.cores, params.memoriaL1, params.memoriaL2)
    env.run()
    throughput, avg_service_time, core_usage_percent = procesador.resultados()
    print(f"Throughput: {throughput}")
    print(f"Tiempo de servicio promedio: {avg_service_time:.4f}")
    print(f"Uso de los cores (%): {core_usage_percent}")
    print("="*100, "\n")
    print(f"Tiempo de ejecución: {time.time()-start:.4f} segundos")

if __name__ == "__main__":
    main()