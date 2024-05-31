import simpy
from rich.console import Console
from rich.table import Table
import argparse
import numpy as np
import string
import os

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
        self.tespera = 0  # Simulación de t_espera
        self.tfinalizacion = 0  # Simulación de t_finalizacion

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

class Procesador(object):
    def __init__(self, env: simpy.Environment, procesos: int, cores: int, memoriaL1: int, memoriaL2: int):
        self.env = env
        self.procesos = procesos
        self.cores = [Core(i, memoriaL1, memoriaL2) for i in range(cores)]
        self.memoriaL1 = memoriaL1
        self.memoriaL2 = memoriaL2
        self.cola = simpy.Store(env)
        self.env.process(self.run())
        self.throughput = 0
        self.total_service_time = 0
        self.usoCore = np.zeros(cores).tolist()

    def run(self):
        for idProceso in range(self.procesos):
            self.env.process(self.crear_proceso(idProceso))
        yield self.env.timeout(0)

    def crear_proceso(self, idProceso: int):
        proceso = Proceso(self.env, idProceso)
        letras = [dato[0] for dato in proceso.datos]
        Debug.log(self.env, f"Proceso id:{idProceso} creado con {proceso.num_datos} datos. Datos = {letras}")
        yield self.env.timeout(0)
        self.env.process(self.asignar_proceso(proceso))

    def asignar_proceso(self, proceso: Proceso):
        while True:
            core = self.assign()
            if core:
                start_time = self.env.now
                proceso.tespera = start_time
                for data in proceso.datos:
                    yield self.env.process(self.use_data(core, data))
                end_time = self.env.now
                proceso.tfinalizacion = end_time
                service_time = end_time - start_time
                self.total_service_time += service_time
                self.usoCore[core.idCore] += service_time
                self.throughput += 1
                self.success(core)
                Debug.log(self.env, f"Proceso id:{proceso.idProceso} terminado. Tiempo de servicio: {service_time:.4f}")
                break
            else:
                yield self.env.timeout(1)
        yield self.env.timeout(0)

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
        for core in self.cores:
            if not core.inUse:
                core.inUse = True
                return core
        return None

    def success(self, core: Core):
        core.inUse = False

    def resultados(self):
        tServicioPromedio = self.total_service_time / self.procesos if self.procesos > 0 else 0
        usoCore = [round((uso),4) for uso in self.usoCore]
        self.throughput = self.throughput / self.env.now
        return self.throughput, tServicioPromedio, usoCore


def main():
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
    throughput, tServicioPromedio, usoCore = procesador.resultados()
    print(f"Throughput: {throughput:.4f}")
    print(f"Tiempo de servicio promedio: {tServicioPromedio:.4f}")
    cons=Console()
    table = Table(title="Uso de los cores", show_header=True, header_style="bold magenta")
    table.add_column("Core", style="dim", width=12)
    table.add_column("Uso (Ciclos de reloj)", justify="right")
    for i,j in enumerate(usoCore):
        table.add_row(str(i),str(j))
    cons.print(table)

if __name__ == "__main__":
    main()