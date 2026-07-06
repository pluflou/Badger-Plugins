"""LCLS FEL pulse-energy surrogate environment.

Enumerates the surrogate model's 341 inputs as Badger variables (bounds from the
model's value ranges) and its single output (GDET:FEE1:241:ENRC) as an observable.
The model is loaded only to read this metadata; all reads/writes go through the
epics interface (see configs.yaml) to the lume-pva PV server, not in-process.
"""

from badger import environment
from lcls_fel_model import load_model

_model = load_model()


class Environment(environment.Environment):
    name = "lcls_fel_surrogate"

    variables = {}
    observables = []
