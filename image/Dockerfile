FROM ubuntu:22.04
WORKDIR /app

# Install dependencies
RUN apt-get update && \
    apt-get install -y build-essential wcslib-dev git python3 python3-pip

# Clone & install SoFiA-2
RUN git clone https://gitlab.com/SoFiA-Admin/SoFiA-2.git
RUN cd SoFiA-2 && \
    ./compile.sh -fopenmp && \
    ln -s /app/SoFiA-2/sofia /usr/bin/sofia

# Install profiling tools
COPY requirements.txt .
RUN pip install -r requirements.txt

# Run
ENTRYPOINT ["sofia"]
