from dataclasses import dataclass, Field, fields
from pathlib import Path
from defusedxml.ElementTree import parse
from offline_conf_reader.oks_utils import find_session, check_for_data_includes, get, get_value

detector_types = ['CRP', 'APA']

def get_application(root, session, application_name):
    selected_applications = []

    root_segment = get(root, session, "segment")
    segments = get(root, root_segment, "segments")
    for segment in segments:
        applications = get(root, segment, "applications")
        for application in applications:
            if application.attrib['class'] == application_name:
                selected_applications += [application]

    return selected_applications


@dataclass
class DUNEDAQConfDataExtractor:
    oks_file_path: Path
    session_name:str
    buffer               : object = None
    ac_couple            : dict[str,bool] = None
    pulse_dac            : object = None
    pulser               : dict[str,bool] = None
    baseline             : dict[str,int]  = None
    gain                 : dict[str,int]  = None
    leak                 : object = None
    leak_10x             : dict[str,bool] = None
    peak_time            : dict[str,int]  = None
    enable_femb_fake_data: object = None
    test_cap             : dict[str,bool] = None
    APAs                 : list[int] = None
    FEMBs                : object = None
    pulse_period         : dict[str,int]  = None
    phase_group          : object = None
    phases               : object = None

    def __post_init__(self):
        if self.oks_file_path == 'dummy':
            return

        self.ac_couple    = {}
        self.pulser       = {}
        self.baseline     = {}
        self.gain         = {}
        self.leak_10x     = {}
        self.peak_time    = {}
        self.test_cap     = {}
        self.pulse_period = {}
        self.APAs         = []

        tree = parse(self.oks_file_path)
        root = tree.getroot()

        if check_for_data_includes(root):
            raise RuntimeError('Include files are not supported, the configuration was not consolidated!')

        session = find_session(root, self.session_name)
        wiec_applications = get_application(root, session, "WIECApplication")

        for wiec_application in wiec_applications:
            wiec_application_name = wiec_application.attrib['id']
            wib_module_conf = get(root, wiec_application, "wib_module_conf")
            wib_settings = get(root, wib_module_conf, "settings")

            pulser_setting = get(root, wib_settings, "pulser")
            self.pulser[wiec_application_name] = get_value(pulser_setting)

            wib_pulser_setting = get(root, wib_settings, "wib_pulser")
            self.pulse_period[wiec_application_name] = get_value(
                get(root, wib_pulser_setting, "pulse_period")
            )

            fembs =  [get(root, wib_settings, "femb0")]
            fembs += [get(root, wib_settings, "femb1")]
            fembs += [get(root, wib_settings, "femb2")]
            fembs += [get(root, wib_settings, "femb3")]

            self.extract_femb_variables(root, self.leak_10x , "leak_10x" , fembs, wiec_application_name)
            self.extract_femb_variables(root, self.ac_couple, "ac_couple", fembs, wiec_application_name)
            self.extract_femb_variables(root, self.peak_time, "peak_time", fembs, wiec_application_name)
            self.extract_femb_variables(root, self.baseline , "baseline" , fembs, wiec_application_name)
            self.extract_femb_variables(root, self.test_cap , "test_cap" , fembs, wiec_application_name)


        ru_applications = get_application(root, session, "ReadoutApplication")
        for ru_application in ru_applications:
            contains = get(root, ru_application, "contains")
            connections = [contain.attrib['id'].upper().replace('_', "-") for contain in contains]
            for connection in connections:
                for i in connection.split('-'):
                    for detector_type in detector_types:
                        if detector_type in i:
                            self.APAs += [i]

    def extract_femb_variables(self, root, field, name, fembs, prefix):
        for i, femb in enumerate(fembs):
            field[prefix+f"_femb{i}"] = get_value(get(root, femb, name))


    def get_variables(self) -> list[Field]:

        data = []
        for field in fields(self):
            if field.name == 'session_name' or field.name == 'oks_file_path':
                continue
            data += [field]

        return data
