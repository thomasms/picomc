import matplotlib.pyplot as plt
import numpy as np


block_size = 100.0
num_bins = 10  # voxels per dimension
mid = num_bins // 2
voxel_size = block_size / num_bins

flux_tally = np.zeros((num_bins, num_bins, num_bins))

# Neutron velocities (cm/s), approximate:
velocities = {
    0: 2e7,   # fast neutrons ~20,000 km/s
    1: 2.2e5  # thermal neutrons ~2200 m/s
}

# Cross sections for two energy groups (fast = 0, thermal = 1)
# Values are macroscopic cross sections in cm^-1
#  Numbers are complete nonsense but serve for illustration only
cross_sections = {
    0: {'sigma_s': 0.08, 'sigma_a': 0.01, 'sigma_f': 0.01},  # fast
    1: {'sigma_s': 0.1,  'sigma_a': 0.04, 'sigma_f': 0.01}   # thermal
}

def voxel_indices(pos):
    # Clamp indices inside the grid
    ix = min(max(int(pos[0] / voxel_size), 0), num_bins-1)
    iy = min(max(int(pos[1] / voxel_size), 0), num_bins-1)
    iz = min(max(int(pos[2] / voxel_size), 0), num_bins-1)
    return ix, iy, iz

def tally_flux(pos_start, pos_end):
    # Approximate: tally full path length in voxel where neutron started
    # (More accurate ray tracing can be implemented if needed)
    dist = np.linalg.norm(pos_end - pos_start)
    ix, iy, iz = voxel_indices(pos_start)
    flux_tally[ix, iy, iz] += dist

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
time = 0.0

for _ in range(num_source):
    position = np.array([block_size/2, block_size/2, block_size/2])
    direction = sample_direction()
    energy_group = 0  # start all fast
    time = 0.0
    particle_bank.append((position, direction, energy_group, time))

absorbed = 0
escaped = 0
fission_events = 0
total_neutrons = 0

while particle_bank:
    position, direction, energy_group, time = particle_bank.pop()
    alive = True
    total_neutrons += 1
    
    while alive:
        sigma_t = total_sigma(energy_group)
        d = sample_distance(sigma_t)
        new_pos = position + direction * d

        if np.any(new_pos < 0) or np.any(new_pos > block_size):
            # Calculate distance traveled inside block (to boundary)
            dist_to_boundary = None
            # Calculate exact distance to boundary for flux tally:
            distances = []
            for i in range(3):
                if direction[i] > 0:
                    dist_bound = (block_size - position[i]) / direction[i]
                elif direction[i] < 0:
                    dist_bound = -position[i] / direction[i]
                else:
                    dist_bound = np.inf
                distances.append(dist_bound)
            dist_to_boundary = min(distances)

            # Tally flux for path inside block
            end_pos = position + direction * dist_to_boundary
            tally_flux(position, end_pos)
            
            # Update time for traveled distance inside block
            time += dist_to_boundary / velocities[energy_group]
            
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
                particle_bank.append((position.copy(), new_dir, 0, time))


# Normalize flux tally by voxel volume and source neutrons
voxel_volume = voxel_size**3
flux_tally /= (voxel_volume * num_source)

print(f"Total neutrons tracked: {total_neutrons}")
print(f"Absorbed: {absorbed} ({absorbed/total_neutrons*100:.2f}%)")
print(f"Escaped: {escaped} ({escaped/total_neutrons*100:.2f}%)")
print(f"Fission events: {fission_events}")



fig, axs = plt.subplots(1, 3, figsize=(18, 6))

# XY slice at middle Z
im0 = axs[0].imshow(flux_tally[:, :, mid].T, origin='lower',
                    extent=[0, block_size, 0, block_size],
                    cmap='inferno')
axs[0].set_title('Flux distribution (XY plane, Z=middle)')
axs[0].set_xlabel('X (cm)')
axs[0].set_ylabel('Y (cm)')
fig.colorbar(im0, ax=axs[0], fraction=0.046, pad=0.04)

# XZ slice at middle Y
im1 = axs[1].imshow(flux_tally[:, mid, :].T, origin='lower',
                    extent=[0, block_size, 0, block_size],
                    cmap='inferno')
axs[1].set_title('Flux distribution (XZ plane, Y=middle)')
axs[1].set_xlabel('X (cm)')
axs[1].set_ylabel('Z (cm)')
fig.colorbar(im1, ax=axs[1], fraction=0.046, pad=0.04)

# YZ slice at middle X
im2 = axs[2].imshow(flux_tally[mid, :, :].T, origin='lower',
                    extent=[0, block_size, 0, block_size],
                    cmap='inferno')
axs[2].set_title('Flux distribution (YZ plane, X=middle)')
axs[2].set_xlabel('Y (cm)')
axs[2].set_ylabel('Z (cm)')
fig.colorbar(im2, ax=axs[2], fraction=0.046, pad=0.04)

plt.tight_layout()
plt.show()
