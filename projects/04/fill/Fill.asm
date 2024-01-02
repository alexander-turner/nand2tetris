// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Fill.asm

// Runs an infinite loop that listens to the keyboard input.
// When a key is pressed (any key), the program blackens the screen
// by writing 'black' in every pixel;
// the screen should remain fully black as long as the key is pressed. 
// When no key is pressed, the program clears the screen by writing
// 'white' in every pixel;
// the screen should remain fully clear as long as no key is pressed.
// TODO just compute total number of registers? 

// Initialize row and column to 0
@0 
D=A 
@row 
M=D 
@col 
M=D 

// Set initial pixel RAM address
@SCREEN
D=A
@pixAddress
M=D

(LISTEN)
    // Check if a key is pressed 
    @KBD 
    D=M 

    @BLACK 
    D;JNE // Nonzero code from keyboard 
(WHITE)
    @0 
    D=A 
    // clear the current pixel  
    @pixAddress
    A=M // Load the address 
    M=D // Set register to 0

    @INCREMENT
    0;JMP
(BLACK)
    @pixAddress 
    A=M // Load the address 
    M=-1
(INCREMENT)
    // Increment pixel 
    @pixAddress
    M=M+1
    // Go to the next chunk of pixels by incrementing row, col 
    @16
    D=A 
    @col
    M=M+D


    // There are 256 rows, 512 cols. 
    // Check if need to roll col to 0
    D=M // Load col into data register
    @512 
    D=D-A 
    @LISTEN 
    D;JLT // if col - 512 < 0, then go back to LISTEN
(COLRESET)
    @0
    D=A
    @col
    M=D 

    // increment row and see if need to reset
    @row 
    M=M+1
    D=M 
    @256
    D=D-A // row - 256 
    // Need to reset if row >= 256 (if D >= 0)
    // If don't need to reset, go back to LISTEN    
    @LISTEN
    D;JLT
(ROWRESET)
    @0
    D=A
    @row
    M=D

    // Set pixel to SCREEN address 
    @SCREEN
    D=A
    @pixAddress 
    M=D 

    @LISTEN 
    0;JMP  
