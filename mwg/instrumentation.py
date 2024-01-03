from code_generator import CodeGenerator


class NoInstrumentation:
    def initialize(self, generator: CodeGenerator):
        pass

    def start_region(self, generator: CodeGenerator, region_name: str):
        pass

    def read_region(self, generator: CodeGenerator, region_name: str):
        pass

    def end_region(self, generator: CodeGenerator, region_name: str):
        pass

    def finalize(self, generator: CodeGenerator):
        pass

    def get_compiler_flags(self) -> list:
        return []

    def get_linker_flags(self) -> list:
        return []

    def __repr__(self):
        return "none"


class PAPIInstrumentation(NoInstrumentation):
    """
    Instrumentation using the PAPI High-Level API
    """
    def initialize(self, generator: CodeGenerator):
        generator.include("papi.h", sys=False)
        generator.include("stdio.h", sys=True)

    def start_region(self, generator: CodeGenerator, region_name: str):
        generator.add_line(f"if(PAPI_hl_region_begin(\"{region_name}\") != PAPI_OK) {{ printf(\"Failed to begin PAPI region {region_name}\\n\"); }}")

    def read_region(self, generator: CodeGenerator, region_name: str):
        generator.add_line(f"if(PAPI_hl_read(\"{region_name}\") != PAPI_OK) {{ printf(\"Failed to read PAPI region {region_name}\\n\"); }}")

    def end_region(self, generator: CodeGenerator, region_name: str):
        generator.add_line(f"if(PAPI_hl_region_end(\"{region_name}\") != PAPI_OK) {{ printf(\"Failed to end PAPI region {region_name}\\n\"); }}")

    def finalize(self, generator: CodeGenerator):
        generator.add_line("if(PAPI_hl_stop() != PAPI_OK) { printf(\"Failed to stop PAPI hl API\"); }")

    def get_linker_flags(self) -> list:
        return ["-lpapi"]

    def __repr__(self):
        return "papi"



class LikwidInstrumentation(NoInstrumentation):
    """
    Instrumentation using the LIKWID marker api
    """
    def initialize(self, generator: CodeGenerator):
        generator.include("likwid-marker.h", sys=True)
        generator.add_line("likwid_markerInit();")  # TODO: Maybe threaded init here

    def start_region(self, generator: CodeGenerator, region_name: str):
        generator.add_line(f"likwid_markerStartRegion(\"{region_name}\");")

    def end_region(self, generator: CodeGenerator, region_name: str):
        generator.add_line(f"likwid_markerStopRegion(\"{region_name}\");")

    def finalize(self, generator: CodeGenerator):
        generator.add_line("likwid_markerClose();")

    def get_compiler_flags(self) -> list:
        return ["-DLIKWID_PERFMON"]

    def get_linker_flags(self) -> list:
        return ["-llikwid"]

    def __repr__(self):
        return "likwid"


registered_instrumentation_methods = {"papi": PAPIInstrumentation(), "likwid": LikwidInstrumentation()}


def get_registered(name):
    if name is None:
        return NoInstrumentation()
    if name.lower() in registered_instrumentation_methods:
        return registered_instrumentation_methods[name.lower()]
    raise AttributeError(f"Invalid instrumentation '{name}'")
