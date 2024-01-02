// Program: Mult.hack 
// Computes: RAM[2] = RAM[0] times RAM[1]
// Usage: put values in RAM[0] and RAM[1]
    // Get zero constant 
    @0 
    D=A 
    // Put it into a @count variable 
    @count
    M=D 

    @R2 
    M=D 

(LOOP)
    @count 
    D=M 

    @R0 
    D=D-M

    @END 
    D;JGE 
    // If count - RAM[0] >= 0 (count >= RAM[0]), then jump 
    
    // Read the RAM[1] value and put it in data register 
    @R1 
    D=M 

    // Add to RAM[2]
    @R2
    M=M+D 
    
    // Increment count 
    @count 
    M=M+1 

    @LOOP 
    0;JMP 
(END)
    @END 
    0;JMP
    
