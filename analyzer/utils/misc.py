def model_to_dict(model):
    result = dict(model.__dict__)
    result.pop("_sa_instance_state", None)
    return result
