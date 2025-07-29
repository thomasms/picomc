import numpy as np

block_size = 10.0

# Cross sections for two energy groups (fast = 0, thermal = 1)
# Values are macroscopic cross sections in cm^-1
#  Numbers are complete nonsense but serve for illustration only
cross_sections = {
    0: {'sigma_s': 0.08, 'sigma_a': 0.01, 'sigma_f': 0.01},  # fast
    1: {'sigma_s': 0.1,  'sigma_a': 0.04, 'sigma_f': 0.01}   # thermal
}

def total_sigma(energy_group):
    cs = cross_sections[energy_group]
    return cs['sigma_s'] + cs['sigma_a'] + cs['sigma_f']

def sample_distance(sigma_t):
    xi = np.random.random()
    return -np.log(xi) / sigma_t

def sample_interaction(energy_group):
    cs = cross_sections[energy_group]
    xi = np.random.random()
    sigma_t = total_sigma(energy_group)
    if xi < cs['sigma_s'] / sigma_t:
        return "scatter"
    elif xi < (cs['sigma_s'] + cs['sigma_a']) / sigma_t:
        return "absorb"
    else:
        return "fission"

def sample_direction():
    phi = 2 * np.pi * np.random.random()
    cos_theta = 2 * np.random.random() - 1
    sin_theta = np.sqrt(1 - cos_theta**2)
    dx = sin_theta * np.cos(phi)
    dy = sin_theta * np.sin(phi)
    dz = cos_theta
    return np.array([dx, dy, dz])

def sample_num_fission_neutrons():
    # utter nonsense
    return np.random.poisson(2.5)

def scatter_energy(energy_group):
    # Fast group neutrons have 30% chance to downscatter to thermal group
    if energy_group == 0 and np.random.random() < 0.3:
        return 1  # downscatter to thermal
    return energy_group  # stay in same group

# Particle bank: each particle = (position, direction, energy_group)
num_source = 1000
particle_bank = []
for _ in range(num_source):
    position = np.array([block_size/2, block_size/2, block_size/2])
    direction = sample_direction()
    energy_group = 0  # start all fast
    particle_bank.append((position, direction, energy_group))

absorbed = 0
escaped = 0
fission_events = 0
total_neutrons = 0

while particle_bank:
    position, direction, energy_group = particle_bank.pop()
    alive = True
    total_neutrons += 1
    
    while alive:
        sigma_t = total_sigma(energy_group)
        d = sample_distance(sigma_t)
        new_pos = position + direction * d
        
        if np.any(new_pos < 0) or np.any(new_pos > block_size):
            escaped += 1
            alive = False
            break
        
        position = new_pos
        interaction = sample_interaction(energy_group)
        
        if interaction == "absorb":
            absorbed += 1
            alive = False
            
        elif interaction == "scatter":
            direction = sample_direction()
            energy_group = scatter_energy(energy_group)
            
        else:  # fission
            fission_events += 1
            alive = False
            num_new = sample_num_fission_neutrons()
            for _ in range(num_new):
                new_dir = sample_direction()
                # Fission neutrons assumed born in fast group
                particle_bank.append((position.copy(), new_dir, 0))

print(f"Total neutrons tracked: {total_neutrons}")
print(f"Absorbed: {absorbed} ({absorbed/total_neutrons*100:.2f}%)")
print(f"Escaped: {escaped} ({escaped/total_neutrons*100:.2f}%)")
print(f"Fission events: {fission_events}")

