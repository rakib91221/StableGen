import random

# Prompt for ComfyUI in API format (SDXL)
prompt_text = """
        {
            "5": {
                "inputs": {
                    "image": "",
                    "upload": "image"
                },
                "class_type": "LoadImage",
                "_meta": {
                    "title": "Load Image"
                }
            },
            "6": {
                "inputs": {
                    "ckpt_name": "sd_xl_base_1.0.safetensors"
                },
                "class_type": "CheckpointLoaderSimple",
                "_meta": {
                    "title": "Load Checkpoint"
                }
            },
            "9": {
                "inputs": {
                    "text": "a monkey",
                    "clip": [
                        "247",
                        0
                    ]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {
                    "title": "CLIP Text Encode (Prompt)"
                }
            },
            "10": {
                "inputs": {
                    "text": "",
                    "clip": [
                        "247",
                        0
                    ]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {
                    "title": "CLIP Text Encode (Prompt)"
                }
            },
            "15": {
                "inputs": {
                    "seed": 24,
                    "steps": 8,
                    "cfg": 1.5,
                    "sampler_name": "dpmpp_2s_ancestral",
                    "scheduler": "sgm_uniform",
                    "denoise": 1,
                    "model": [
                        "26",
                        0
                    ],
                    "positive": [
                        "14",
                        0
                    ],
                    "negative": [
                        "14",
                        1
                    ],
                    "latent_image": [
                        "16",
                        0
                    ]
                },
                "class_type": "KSampler",
                "_meta": {
                    "title": "KSampler"
                }
            },
            "16": {
                "inputs": {
                    "width": 1024,
                    "height": 1024,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage",
                "_meta": {
                    "title": "Empty Latent Image"
                }
            },
            "19": {
                "inputs": {
                    "samples": [
                        "15",
                        0
                    ],
                    "vae": [
                        "6",
                        2
                    ]
                },
                "class_type": "VAEDecode",
                "_meta": {
                    "title": "VAE Decode"
                }
            },
            "25": {
                "inputs": {
                    "images": [
                        "19",
                        0
                    ]
                },
                "class_type": "SaveImageWebsocket",
                "_meta": {
                    "title": "SaveImageWebsocket"
                }
            },
            "27": {
                "inputs": {
                    "image": "",
                    "upload": "image"
                },
                "class_type": "LoadImage",
                "_meta": {
                    "title": "Load Image"
                }
            },
            "239": {
                "inputs": {
                    "type": "depth",
                    "control_net": [
                        "201",
                        0
                    ]
                },
                "class_type": "SetUnionControlNetType",
                "_meta": {
                    "title": "SetUnionControlNetType"
                }
            },
            "247": {
                "inputs": {
                  "stop_at_clip_layer": -1,
                  "clip": [
                    "",
                    1
                  ]
                },
                "class_type": "CLIPSetLastLayer",
                "_meta": {
                  "title": "CLIP Set Last Layer"
                }
            },
            "235": {
              "inputs": {
                "preset": "PLUS (high strength)",
                "model": [
                  "",
                  0
                ]
              },
              "class_type": "IPAdapterUnifiedLoader",
              "_meta": {
                "title": "IPAdapter Unified Loader"
              }
            },
            "236": {
              "inputs": {
                "weight": 1,
                "start_at": 0,
                "end_at": 1,
                "weight_type": "standard",
                "model": [
                  "235",
                  0
                ],
                "ipadapter": [
                  "235",
                  1
                ],
                "image": ["237", 0]
              },
              "class_type": "IPAdapter",
              "_meta": {
                "title": "IPAdapter"
              }
            },
            "237": {
              "inputs": {
                "upload": "image"
              },
              "class_type": "LoadImage",
              "_meta": {
                "title": "Load Image"
              }
            }
        }
        """

prompt_text_img2img = """
{
  "1": {
      "inputs": {
        "image": "",
        "upload": "image"
      },
      "class_type": "LoadImage",
      "_meta": {
        "title": "Load Image"
      }
    },
  "12": {
      "inputs": {
        "image": "",
        "upload": "image"
      },
      "class_type": "LoadImage",
      "_meta": {
        "title": "Load Image"
      }
    },
  "23": {
      "inputs": {
        "upscale_method": "nearest-exact",
        "width": 1024,
        "height": 1024,
        "crop": "disabled",
        "image": [
          "1",
          0
        ]
      },
      "class_type": "ImageScale",
      "_meta": {
        "title": "Upscale Image"
      }
    },
  "13": {
    "inputs": {
      "grow_mask_by": 0,
      "pixels": [
        "23",
        0
      ],
      "vae": [
        "38",
        2
      ],
      "mask": [
        "25",
        0
      ]
    },
    "class_type": "VAEEncodeForInpaint",
    "_meta": {
      "title": "VAE Encode (for Inpainting)"
    }
  },
  "25": {
    "inputs": {
      "channel": "red",
      "image": [
        "12",
        0
      ]
    },
    "class_type": "ImageToMask",
    "_meta": {
      "title": "Convert Image to Mask"
    }
  },
  "38": {
    "inputs": {
      "ckpt_name": "realvisxlV40_v40Bakedvae.safetensors"
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {
      "title": "Load Checkpoint"
    }
  },
  "102": {
    "inputs": {
      "text": "tifa lockhart, cosplay, final fantasy",
      "clip": [
        "247",
        0
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "103": {
    "inputs": {
      "text": "",
      "clip": [
        "247",
        0
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "105": {
    "inputs": {
      "seed": 42,
      "steps": 8,
      "cfg": 1.48,
      "sampler_name": "dpmpp_sde",
      "scheduler": "sgm_uniform",
      "denoise": 0.5,
      "model": [
        "",
        0
      ],
      "positive": [
        "104",
        0
      ],
      "negative": [
        "104",
        1
      ],
      "latent_image": [
        "116",
        0
      ]
    },
    "class_type": "KSampler",
    "_meta": {
      "title": "KSampler"
    }
  },
  "108": {
    "inputs": {
      "image": "",
      "upload": "image"
    },
    "class_type": "LoadImage",
    "_meta": {
      "title": "Load Image"
    }
  },
  "110": {
    "inputs": {
      "samples": [
        "105",
        0
      ],
      "vae": [
        "38",
        2
      ]
    },
    "class_type": "VAEDecode",
    "_meta": {
      "title": "VAE Decode"
    }
  },
  "111": {
    "inputs": {
      "images": [
        "110",
        0
      ]
    },
    "class_type": "SaveImageWebsocket",
    "_meta": {
        "title": "SaveImageWebsocket"
    }
  },
  "116": {
    "inputs": {
      "pixels": [
        "118",
        0
      ],
      "vae": [
        "38",
        2
      ]
    },
    "class_type": "VAEEncode",
    "_meta": {
      "title": "VAE Encode"
    }
  },
  "117": {
    "inputs": {
      "image": "",
      "upload": "image"
    },
    "class_type": "LoadImage",
    "_meta": {
      "title": "Load Image"
    }
  },
  "118": {
    "inputs": {
      "upscale_method": "lanczos",
      "width": 713,
      "height": 1080,
      "crop": "disabled",
      "image": [
        "117",
        0
      ]
    },
    "class_type": "ImageScale",
    "_meta": {
      "title": "Upscale Image"
    }
  },
  "224": {
    "inputs": {
      "expand": 0,
      "tapered_corners": true,
      "mask": [
        "25",
        0
      ]
    },
    "class_type": "GrowMask",
    "_meta": {
      "title": "GrowMask"
    }
  },
  "225": {
    "inputs": {
      "mask": [
        "224",
        0
      ]
    },
    "class_type": "MaskToImage",
    "_meta": {
      "title": "Convert Mask to Image"
    }
  },
  "226": {
    "inputs": {
      "blur_radius": 1,
      "sigma": 1,
      "image": [
        "225",
        0
      ]
    },
    "class_type": "ImageBlur",
    "_meta": {
      "title": "Image Blur"
    }
  },
  "227": {
    "inputs": {
      "channel": "red",
      "image": [
        "226",
        0
      ]
    },
    "class_type": "ImageToMask",
    "_meta": {
      "title": "Convert Image to Mask"
    }
  },
  "228": {
    "inputs": {
      "noise_mask": true,
      "positive": [
        "102",
        0
      ],
      "negative": [
        "103",
        0
      ],
      "vae": [
        "38",
        2
      ],
      "pixels": [
        "1",
        0
      ],
      "mask": [
        "227",
        0
      ]
    },
    "class_type": "InpaintModelConditioning",
    "_meta": {
      "title": "InpaintModelConditioning"
    }
  },
  "229": {
    "inputs": {
      "model": [
        "",
        0
      ]
    },
    "class_type": "DifferentialDiffusion",
    "_meta": {
      "title": "Differential Diffusion"
    }
  },
  "235": {
    "inputs": {
      "preset": "PLUS (high strength)",
      "model": [
        "",
        0
      ]
    },
    "class_type": "IPAdapterUnifiedLoader",
    "_meta": {
      "title": "IPAdapter Unified Loader"
    }
  },
  "236": {
    "inputs": {
      "weight": 1,
      "start_at": 0,
      "end_at": 1,
      "weight_type": "standard",
      "model": [
        "235",
        0
      ],
      "ipadapter": [
        "235",
        1
      ],
      "image": ["1", 0]
    },
    "class_type": "IPAdapter",
    "_meta": {
      "title": "IPAdapter"
    }
  },
  "237": {
    "inputs": {
      "upload": "image"
    },
    "class_type": "LoadImage",
    "_meta": {
      "title": "Load Image"
    }
  },
  "239": {
    "inputs": {
      "type": "depth",
      "control_net": [
        "201",
        0
      ]
    },
    "class_type": "SetUnionControlNetType",
    "_meta": {
      "title": "SetUnionControlNetType"
    }
  },
  "247": {
    "inputs": {
      "stop_at_clip_layer": -1,
      "clip": [
        "",
        1
      ]
    },
    "class_type": "CLIPSetLastLayer",
    "_meta": {
      "title": "CLIP Set Last Layer"
    }
  }
}
"""

prompt_text_flux = """ {
  "6": {
    "inputs": {
      "text": "a monkey",
      "clip": [
        "11",
        0
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Positive Prompt)"
    }
  },
  "8": {
    "inputs": {
      "samples": [
        "13",
        0
      ],
      "vae": [
        "10",
        0
      ]
    },
    "class_type": "VAEDecode",
    "_meta": {
      "title": "VAE Decode"
    }
  },
  "10": {
    "inputs": {
      "vae_name": "ae.sft"
    },
    "class_type": "VAELoader",
    "_meta": {
      "title": "Load VAE"
    }
  },
  "11": {
    "inputs": {
      "clip_name1": "t5xxl_fp8_e4m3fn.safetensors",
      "clip_name2": "clip_l.safetensors",
      "type": "flux",
      "device": "default"
    },
    "class_type": "DualCLIPLoader",
    "_meta": {
      "title": "DualCLIPLoader"
    }
  },
  "12": {
    "inputs": {
      "unet_name": "flux1-dev.sft",
      "weight_dtype": "default"
    },
    "class_type": "UNETLoader",
    "_meta": {
      "title": "Load Diffusion Model"
    }
  },
  "13": {
    "inputs": {
      "noise": [
        "25",
        0
      ],
      "guider": [
        "22",
        0
      ],
      "sampler": [
        "16",
        0
      ],
      "sigmas": [
        "17",
        0
      ],
      "latent_image": [
        "30",
        0
      ]
    },
    "class_type": "SamplerCustomAdvanced",
    "_meta": {
      "title": "SamplerCustomAdvanced"
    }
  },
  "16": {
    "inputs": {
      "sampler_name": "euler"
    },
    "class_type": "KSamplerSelect",
    "_meta": {
      "title": "KSamplerSelect"
    }
  },
  "17": {
    "inputs": {
      "scheduler": "simple",
      "steps": 21,
      "denoise": 1,
      "model": [
        "12",
        0
      ]
    },
    "class_type": "BasicScheduler",
    "_meta": {
      "title": "BasicScheduler"
    }
  },
  "22": {
    "inputs": {
      "model": [
        "12",
        0
      ],
      "conditioning": [
        "26",
        0
      ]
    },
    "class_type": "BasicGuider",
    "_meta": {
      "title": "BasicGuider"
    }
  },
  "25": {
    "inputs": {
      "noise_seed": 42
    },
    "class_type": "RandomNoise",
    "_meta": {
      "title": "RandomNoise"
    }
  },
  "26": {
    "inputs": {
      "guidance": 40,
      "conditioning": [
        "6",
        0
      ]
    },
    "class_type": "FluxGuidance",
    "_meta": {
      "title": "FluxGuidance"
    }
  },
  "30": {
    "inputs": {
      "width": 1024,
      "height": 1024,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage",
    "_meta": {
      "title": "Empty Latent Image"
    }
  },
  "32": {
    "inputs": {
      "images": [
        "8",
        0
      ]
    },
    "class_type": "SaveImageWebsocket",
    "_meta": {
      "title": "SaveImageWebsocket"
    }
  },
  "239": {
    "inputs": {
      "type": "",
      "control_net": [
        "201",
        0
      ]
    },
    "class_type": "SetUnionControlNetType",
    "_meta": {
      "title": "SetUnionControlNetType"
    }
  }
}
"""

prompt_text_img2img_flux = """ {
  "1": {
        "inputs": {
          "image": "",
          "upload": "image"
        },
        "class_type": "LoadImage",
        "_meta": {
          "title": "Load Image"
        }
      },
  "6": {
    "inputs": {
      "text": "a monkey",
      "clip": [
        "11",
        0
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Positive Prompt)"
    }
  },
  "8": {
    "inputs": {
      "samples": [
        "13",
        0
      ],
      "vae": [
        "10",
        0
      ]
    },
    "class_type": "VAEDecode",
    "_meta": {
      "title": "VAE Decode"
    }
  },
  "10": {
    "inputs": {
      "vae_name": "ae.sft"
    },
    "class_type": "VAELoader",
    "_meta": {
      "title": "Load VAE"
    }
  },
  "11": {
    "inputs": {
      "clip_name1": "t5xxl_fp8_e4m3fn.safetensors",
      "clip_name2": "clip_l.safetensors",
      "type": "flux",
      "device": "default"
    },
    "class_type": "DualCLIPLoader",
    "_meta": {
      "title": "DualCLIPLoader"
    }
  },
  "12": {
    "inputs": {
      "unet_name": "flux1-dev.sft",
      "weight_dtype": "default"
    },
    "class_type": "UNETLoader",
    "_meta": {
      "title": "Load Diffusion Model"
    }
  },
  "13": {
    "inputs": {
      "noise": [
        "25",
        0
      ],
      "guider": [
        "22",
        0
      ],
      "sampler": [
        "16",
        0
      ],
      "sigmas": [
        "17",
        0
      ],
      "latent_image": [
        "116",
        0
      ]
    },
    "class_type": "SamplerCustomAdvanced",
    "_meta": {
      "title": "SamplerCustomAdvanced"
    }
  },
  "16": {
    "inputs": {
      "sampler_name": "euler"
    },
    "class_type": "KSamplerSelect",
    "_meta": {
      "title": "KSamplerSelect"
    }
  },
  "17": {
    "inputs": {
      "scheduler": "simple",
      "steps": 21,
      "denoise": 1,
      "model": [
        "12",
        0
      ]
    },
    "class_type": "BasicScheduler",
    "_meta": {
      "title": "BasicScheduler"
    }
  },
  "22": {
    "inputs": {
      "model": [
        "12",
        0
      ],
      "conditioning": [
        "26",
        0
      ]
    },
    "class_type": "BasicGuider",
    "_meta": {
      "title": "BasicGuider"
    }
  },
  "25": {
    "inputs": {
      "noise_seed": 42
    },
    "class_type": "RandomNoise",
    "_meta": {
      "title": "RandomNoise"
    }
  },
  "26": {
    "inputs": {
      "guidance": 40,
      "conditioning": [
        "6",
        0
      ]
    },
    "class_type": "FluxGuidance",
    "_meta": {
      "title": "FluxGuidance"
    }
  },
  "30": {
    "inputs": {
      "width": 1024,
      "height": 1024,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage",
    "_meta": {
      "title": "Empty Latent Image"
    }
  },
  "32": {
    "inputs": {
      "images": [
        "8",
        0
      ]
    },
    "class_type": "SaveImageWebsocket",
    "_meta": {
      "title": "SaveImageWebsocket"
    }
  },
  "42": {
      "inputs": {
        "image": "",
        "upload": "image"
      },
      "class_type": "LoadImage",
      "_meta": {
        "title": "Load Image"
      }
    },
  "43": {
      "inputs": {
        "upscale_method": "nearest-exact",
        "width": 1024,
        "height": 1024,
        "crop": "disabled",
        "image": [
          "1",
          0
        ]
      },
      "class_type": "ImageScale",
      "_meta": {
        "title": "Upscale Image"
      }
    },
  "44": {
    "inputs": {
      "grow_mask_by": 0,
      "pixels": [
        "43",
        0
      ],
      "vae": [
        "10",
        0
      ],
      "mask": [
        "45",
        0
      ]
    },
    "class_type": "VAEEncodeForInpaint",
    "_meta": {
      "title": "VAE Encode (for Inpainting)"
    }
  },
  "45": {
    "inputs": {
      "channel": "red",
      "image": [
        "42",
        0
      ]
    },
    "class_type": "ImageToMask",
    "_meta": {
      "title": "Convert Image to Mask"
    }
  },
  "50": {
    "inputs": {
      "model": [
        "12",
        0
      ]
    },
    "class_type": "DifferentialDiffusion",
    "_meta": {
      "title": "Differential Diffusion"
    }
  },
  "51": {
    "inputs": {
      "noise_mask": true,
      "positive": [
        "6",
        0
      ],
      "negative": [
        "6",
        0
      ],
      "vae": [
        "10",
        0
      ],
      "pixels": [
        "1",
        0
      ],
      "mask": [
        "227",
        0
      ]
    },
    "class_type": "InpaintModelConditioning",
    "_meta": {
      "title": "InpaintModelConditioning"
    }
  },
  "116": {
    "inputs": {
      "pixels": [
        "118",
        0
      ],
      "vae": [
        "10",
        0
      ]
    },
    "class_type": "VAEEncode",
    "_meta": {
      "title": "VAE Encode"
    }
  },
  "117": {
    "inputs": {
      "image": "",
      "upload": "image"
    },
    "class_type": "LoadImage",
    "_meta": {
      "title": "Load Image"
    }
  },
  "118": {
    "inputs": {
      "upscale_method": "lanczos",
      "width": 713,
      "height": 1080,
      "crop": "disabled",
      "image": [
        "117",
        0
      ]
    },
    "class_type": "ImageScale",
    "_meta": {
      "title": "Upscale Image"
    }
  },
  "224": {
    "inputs": {
      "expand": 0,
      "tapered_corners": true,
      "mask": [
        "45",
        0
      ]
    },
    "class_type": "GrowMask",
    "_meta": {
      "title": "GrowMask"
    }
  },
  "225": {
    "inputs": {
      "mask": [
        "224",
        0
      ]
    },
    "class_type": "MaskToImage",
    "_meta": {
      "title": "Convert Mask to Image"
    }
  },
  "226": {
    "inputs": {
      "blur_radius": 1,
      "sigma": 1,
      "image": [
        "225",
        0
      ]
    },
    "class_type": "ImageBlur",
    "_meta": {
      "title": "Image Blur"
    }
  },
  "227": {
    "inputs": {
      "channel": "red",
      "image": [
        "226",
        0
      ]
    },
    "class_type": "ImageToMask",
    "_meta": {
      "title": "Convert Image to Mask"
    }
  },
  "239": {
    "inputs": {
      "type": "",
      "control_net": [
        "201",
        0
      ]
    },
    "class_type": "SetUnionControlNetType",
    "_meta": {
      "title": "SetUnionControlNetType"
    }
  }
}
"""

ipadapter_flux = """
{
  "242": {
      "inputs": {
        "ipadapter": "ip-adapter.bin",
        "clip_vision": "google/siglip-so400m-patch14-384",
        "provider": "cuda"
      },
      "class_type": "IPAdapterFluxLoader",
      "_meta": {
        "title": "Load IPAdapter Flux Model"
      }
    },
  "243": {
    "inputs": {
      "weight": 1,
      "start_percent": 0,
      "end_percent": 1,
      "model": [
        "12",
        0
      ],
      "ipadapter_flux": [
        "242",
        0
      ],
      "image": [
        "244",
        0
      ]
    },
    "class_type": "ApplyIPAdapterFlux",
    "_meta": {
      "title": "Apply IPAdapter Flux Model"
    }
  },
  "244": {
    "inputs": {
      "image": "00010-1613580828.jpeg"
    },
    "class_type": "LoadImage",
    "_meta": {
      "title": "Load Image"
    }
  }
}
"""
