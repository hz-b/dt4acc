# Dockerfile.app
# - Creates Conda env from tango.yaml
# - Installs Poetry into that env (no separate venvs)
# - Clones & installs:
#     hz-b/lat2db
#     hz-b/bact-device-models
#     hz-b/bact-twin-architecture
#   (each via `poetry install`)
# - Clones hz-b/dt4acc (no install step shown, change if needed)

FROM condaforge/mambaforge:24.3.0-0

ARG CONDA_ENV=tangoenv
ENV CONDA_ENV=${CONDA_ENV}

SHELL ["/bin/bash", "-c"]

# Copy your environment file into the image (make sure tango.yaml is in the same folder as this Dockerfile)
COPY tango.yaml /tmp/tango.yaml

# Create the Conda environment
RUN mamba env create -f /tmp/tango.yaml -n ${CONDA_ENV} && \
    echo "source /opt/conda/etc/profile.d/conda.sh && conda activate ${CONDA_ENV}" >> /etc/bash.bashrc

# System deps + Poetry in the Conda env
# (git is needed for cloning; build-essentials are handy for projects with native builds)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git build-essential && \
    rm -rf /var/lib/apt/lists/* && \
    conda run -n ${CONDA_ENV} python -V && \
    conda run -n ${CONDA_ENV} pip install --no-cache-dir poetry && \
    # Make Poetry install into the active Conda env instead of its own venv
    conda run -n ${CONDA_ENV} poetry config virtualenvs.create false

WORKDIR /opt


# Clone repos
RUN git clone https://github.com/hz-b/lat2db.git && \
    git clone https://github.com/hz-b/bact-device-models.git && \
    git clone https://github.com/hz-b/bact-twin-architecture.git && \
    git clone --branch backup-before-filterrepo --single-branch https://github.com/hz-b/dt4acc.git

# Install Poetry projects INTO the Conda env
RUN conda run -n ${CONDA_ENV} poetry -C /opt/lat2db install && \
    conda run -n ${CONDA_ENV} poetry -C /opt/bact-device-models install && \
    conda run -n ${CONDA_ENV} poetry -C /opt/bact-twin-architecture install

# Expose the env on PATH for interactive shells
ENV PATH="/opt/conda/envs/${CONDA_ENV}/bin:${PATH}"

# Default command: keep container alive for interactive work
CMD ["bash", "-lc", "echo 'Container ready. Run: conda activate ${CONDA_ENV}'; tail -f /dev/null"]
