def convert_to_native_types(obj):
                """Recursively convert pandas types to native Python types"""
                if isinstance(obj, dict):
                    return {str(k): convert_to_native_types(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [convert_to_native_types(item) for item in obj]
                elif hasattr(obj, 'item'):  # pandas scalars
                    return obj.item()
                elif hasattr(obj, 'tolist'):  # numpy arrays
                    return obj.tolist()
                else:
                    return obj