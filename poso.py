#!/usr/bin/python3
# 
# Generate a PWS for PoSO

# num_poso = Number of PoSO variables
# n = PoSO bound (log)
# m = Number of random values per rep
# reps = Number of repetitions

# Takes the PoSO variables and random variables * reps as inputs as well as the bit decompositions of the sums
# Check that the linear combination of PoSO variables with random variables is less than the PoSO bound
# Repeat reps times with the same PoSO variables and different random variables
# If all checks pass, output 1, else output 0

import sys
import math

def print_inputs(vcount, num_poso, m, reps, f) -> int:
    # Witness variables
    for i in range(num_poso):
        f.write("P V%d = I%d E\n" % (i, i))
        vcount += 1
    # Randomness - m random variables per PoSO rep
    for i in range(m * reps):
        f.write("P V%d = I%d E\n" % (num_poso + i, num_poso + i))
        vcount += 1
    # Variables for bit decomposition - n bits per sum, ceil(num_poos/m) sums per rep
    for i in range(reps * n * math.ceil(num_poso/m)):
        f.write("P V%d = I%d E\n" % (num_poso + m * reps + i, num_poso + m * reps + i))
        vcount += 1

    return vcount

# print out an add tree given a list of inputs
def print_add_tree(fh, ivals, voffset, maxlength=1):
    while len(ivals) > maxlength:
        outs = []
        for idx in range(0, len(ivals) // 2):
            fh.write("P V%d = V%d + V%d E\n" % (voffset, ivals[2*idx], ivals[2*idx+1]))
            outs.append(voffset)
            voffset += 1

        if len(ivals) % 2 != 0:
            outs.append(ivals[-1])

        ivals = outs

    if maxlength > 1:
        return (ivals, voffset)
    else:
        return (ivals[0], voffset)
    
# print out an OR tree given a list of inputs
def print_or_tree(fh, ivals, voffset):
    while len(ivals) > 1:
        outs = []
        for idx in range(0, len(ivals) // 2):
            fh.write("P V%d = V%d OR V%d E\n" % (voffset, ivals[2*idx], ivals[2*idx+1]))
            outs.append(voffset)
            voffset += 1

        if len(ivals) % 2 != 0:
            outs.append(ivals[-1])

        ivals = outs

    return (ivals[0], voffset)

# sum a bit vector into a single field element
def do_addition(fh, ivals, voffset, noconsts):
    ovals = [ivals[0]] + list(range(voffset, voffset + len(ivals) - 1))

    # unnecessary optimization: 2x = x + x
    fh.write("P V%d = V%d + V%d E\n" % (voffset, ivals[1], ivals[1]))
    voffset += 1

    if noconsts:
        expIn = 1
        for ival in ivals[2:]:
            fh.write("P V%d = V%d * V%d E\n" % (voffset, expIn, ival))
            voffset += 1
            expIn += 1
    else:
        exp = 4
        for ival in ivals[2:]:
            fh.write("P V%d = %d * V%d E\n" % (voffset, exp, ival))
            voffset += 1
            exp *= 2

    return print_add_tree(fh, ovals, voffset)

def verify_bits(fh, ivals, voffset):
    outs = []
    for ival in ivals:
        fh.write("P V%d = V%d NOT V%d E\n" % (voffset, ival, ival))
        fh.write("P V%d = V%d * V%d E\n" % (voffset+1, voffset, ival))
        outs.append(voffset+1)
        voffset += 2

    return (outs, voffset)

def print_poso(num_poso, n, m, reps, f):
    vcount = 0
    f.write("// Inputs\n")
    vcount = print_inputs(vcount, num_poso, m, reps, f)

    f.write("// PoSO\n")
    sumchecks = []
    for i in range(reps):
        # PoSO sums
        rep_sums = []
        
        for j in range(math.ceil(num_poso/m)):
            elements_in_sum = []
            for k in range(m):
                idx = j * m + k
                # This will add some random variables for the last PoSO but it's fine for benchmarking
                elements_in_sum.append(idx)

            # Multiply the PoSO variables by the random variables
            dot_prod_vals = []
            for k in range(m):
                f.write("P V%d = V%d * V%d E\n" % (vcount, elements_in_sum[k], num_poso + i * m + k))
                dot_prod_vals.append(vcount)
                vcount += 1

            # Sum the dot_prod_vals
            sum_var, vcount = print_add_tree(f, dot_prod_vals, vcount, 1)
            rep_sums.append(sum_var)

        # Recombine the bits and check if they're equal to the sums
        for j in range(math.ceil(num_poso/m)):
            bits_for_sum = []
            for k in range(n):
                bits_for_sum.append(num_poso + m * reps + i * n + j * n + k)

            sumcheck, vcount = do_addition(f, bits_for_sum, vcount, True)
            f.write("P V%d = V%d E\n" % (sumcheck, rep_sums[j]))

            sumchecks.append(sumcheck)

    # OR of all sumchecks should be 0
    f.write("// Sum checks\n")
    check, vcount = print_or_tree(f, sumchecks, vcount)

    f.write("// Output\n")
    f.write("P V%d = O%d E\n" % (check, 0))


    # for j in range(num_poso):
    #     dp_vals.append(vcount)
    #     f.write("P V%d = V%d * V%d E\n" % (vcount, j, num_poso + i * num_poso + j))
    #     vcount += 1

    # while len(dp_vals) > 1:
    #     outs = []
    #     for i in range(0, len(dp_vals)//2):
    #         f.write("P V%d = V%d + V%d E\n" % (vcount, dp_vals[2*i], dp_vals[2*i+1]))
    #         outs.append(vcount)
    #         vcount += 1

    #     if len(dp_vals) % 2 != 0:
    #         outs.append(dp_vals[-1])

    #     dp_vals = outs
    
    # sums.append(dp_vals[0])
    
    # # Check if the sum is less than the PoSO bound
    # # The bits are already in the input, get the indices
    # bit_vals = []
    # for j in range(n):
    #     bit_vals.append(num_poso + m * reps + i * n + j)
    
    # # Recombine the bits
    # bitchecks, vcount = verify_bits(f, bit_vals, vcount)
    # checks.append(bitchecks)
    
    # # Check if the recombined value is the same as the sum
    # recombined, vcount = do_addition(f, bit_vals, vcount, True)

    # f.write("P V%d = V%d E\n" % (recombined, dp_vals[0]))

    # # OR of all checks should be 0
    # f.write("// Bit checks\n")
    # check, vcount = print_add_tree(f, [x[0] for x in checks], vcount, 1)
    # f.write("P V%d = V%d E\n" % (vcount, check))

    # f.write("// Output\n")
    # for i in range(reps):
    #     f.write("P V%d = O%d E\n" % (vcount, i))
    #     vcount += 1
    
if __name__ == "__main__":
    if len(sys.argv) != 5:
        print ("Usage: %s <num_poso> <n> <m> <reps>" % sys.argv[0])
        sys.exit(-1)

    num_poso = int(sys.argv[1])
    n = int(sys.argv[2])
    m = int(sys.argv[3])
    reps = int(sys.argv[4])

    with open("../virgo-plus/data/poso_%d_%d_%d_%d.pws" % (num_poso, n, m, reps), 'w') as f:
        print_poso(num_poso, n, m, reps, f)