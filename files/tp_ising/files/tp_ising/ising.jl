empty!(DEPOT_PATH)
push!(DEPOT_PATH, string("/tmp/", ENV["USER"], ".julia"), "/usr/local/julia/depot")
push!(LOAD_PATH, "/usr/local/julia/depot")

using Random
using DelimitedFiles
using ArgParse
using HDF5

#-----------------------------------------------------------
#  Read parameters
#-----------------------------------------------------------

s = ArgParseSettings()
@add_arg_table s begin
    "--coupling", "-J"
        arg_type = Float64
        help = "ferromagnetic constant"
        default = 0.5
    "--field"
        help = "external field"
        arg_type = Float64
        default = 0.0
    "--size", "-L"
        help = "system size"
        arg_type = Int
        default = 16
    "--duration", "-T"
        help = "duration of the simulation"
        arg_type = Int
        default = 10000
    "--configs"
        help = "number of configurations to store"
        arg_type = Int
        default = 10
    "--sampling"
        help = "sampling frequency"
        arg_type = Int
        default = 10
    "--one"
        help = "starts with all the spins up"
        action = :store_true
end

parsed_args = parse_args(s)
for (arg,val) in parsed_args
    println("  $arg  =  $val")
end

J = parsed_args["coupling"]
h = parsed_args["field"]
L = parsed_args["size"]
n_it_scaled = parsed_args["duration"]
n_config = parsed_args["configs"]
sampling = parsed_args["sampling"]
random = !parsed_args["one"]

n_it_scaled_s = n_it_scaled ÷ sampling
save_period = n_it_scaled_s ÷ n_config

#-----------------------------------------------------------
#  Main
#-----------------------------------------------------------

#Jc = log(1 + sqrt(2)) / 2

function filename_index(base, n)
    return base * string(n) * ".h5"
end

function find_filename(base)
    file_ind = 1
    while isfile(filename_index(base, file_ind))
        file_ind += 1
    end
    return filename_index(base, file_ind)
end

filename = find_filename("results/simu_")
println(filename)

if random
    spins = rand([-1, 1], L, L)
else
    spins = ones(L, L)
end

function compute_energy(spins, J, h)
    E = -h * sum(spins)
    E -= J * sum(spins .* circshift(spins, (1, 0)))
    E -= J * sum(spins .* circshift(spins, (0, 1)))
    return E
end

function update(spins, L, J, h, n_it)
    rnd = rand(1:L, n_it, 2)
    us = -log.(rand(n_it))
    for (u, (i, j)) in zip(us, eachrow(rnd))
        dE = 2 * spins[i, j] * (h
                + J * (
                    spins[mod1(i+1, L), j]
                    + spins[mod1(i-1, L), j]
                    + spins[i, mod1(j+1, L)]
                    + spins[i, mod1(j-1, L)]
                )
            )
        if dE < u
            spins[i, j] *= -1
        end
    end
end

h5open(filename, "w") do file
    M = Array{Float64}(undef, n_it_scaled_s)
    E = Array{Float64}(undef, n_it_scaled_s)
    C = Array{Int}(undef, n_config, L, L)
    
    j     = 0
    iconf = 1
    
    for i in 1:n_it_scaled_s
        update(spins, L, J, h, sampling*L*L)
        M[i] = sum(spins)/L^2
        E[i] = compute_energy(spins, J, h)/L^2
        
        j += 1
        if j == save_period
            C[iconf, :, :] = spins
            j = 0
            iconf += 1
        end
    end
    
    attributes(file)["J"] = J
    attributes(file)["h"] = h
    attributes(file)["L"] = L
    attributes(file)["T"] = n_it_scaled
    attributes(file)["sampling"] = sampling
    
    file["magnetization"] = M
    file["energy"] = E
    file["config"] = C
end



