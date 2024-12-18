
extern crate libc;
use std::env;
use std::process::Command;
use std::time::Duration;
use std::time::{SystemTime, UNIX_EPOCH};
use std::io;


struct SimplePRNG {
    seed: usize,
}

impl SimplePRNG {
    fn new() -> Self {
        let start = SystemTime::now();
        let since_the_epoch = start.duration_since(UNIX_EPOCH).expect("");
        let seed = (since_the_epoch.as_secs() / 10000) as usize;
        SimplePRNG { seed }
    }

    fn rand(&mut self) -> usize {
        let a: usize = 1664525;
        let c: usize = 1013904223;
        let m: usize = usize::MAX;
        self.seed = (a.wrapping_mul(self.seed).wrapping_add(c)) % m;
        self.seed
    }
}


fn sanitize_for_bash(input: String) -> String {
    let mut input2 = input.replace("\r\n", "").replace("\n", "");
    let mut sanitized = String::from("'");
    for c in input2.chars() {
        match c {
            '\'' => sanitized.push_str("'\\''"),
            _ => sanitized.push(c),
        }
    }
    sanitized.push('\'');
    sanitized.truncate(100);
    sanitized
}


fn print_cow(s: &str) {
    unsafe {
        libc::setreuid(libc::geteuid(), libc::geteuid());
        env::set_var("LC_ALL", "C");
        let s = Command::new("/bin/sh").args(&["-c", &format!("{} {}", "/usr/games/cowsay -w -T -- ", s)]).status().expect("");
        if !s.success() {
            println!("Command exited with non-zero status");
        }
    }
}


fn get_int(prompt: &str) -> usize {
    loop {
        println!("{}", prompt);
        let mut input = String::new();
        if let Ok(_) = io::stdin().read_line(&mut input) {
            match input.trim().parse::<usize>() {
                Ok(num) => return num,
                Err(_) => {
                    println!("Invalid input, please try again.");
                    continue;
                }
            }
        } else {
            println!("Failed to read input, please try again.");
        }
    }
}


fn game(playername: &str){
    let mut prng = SimplePRNG::new();
    prng.rand();
    let mut chars = vec![' '; 1024];
    for _ in 0..3 {
        chars[prng.rand()%1024] = 'X';
    }
    let mut arraymap = chars.iter().collect::<String>();
    let winning_msg = format!("{}{}", "Congratulations! The winner is: ", playername);
    let winning_msg_sanitized = sanitize_for_bash(winning_msg.clone());

    println!("Try to guess where the 3 treasures are! You have 4 guesses.");
    let mut guesses = [0; 4];
    let mut index = 0;
    loop {
        guesses[index] = get_int(&format!("Guess {}:", index + 1));
        if index == 3 {
            break;
        }
        index += 1;
        if guesses[index-1] > 1024 {
            println!("Invalid input, please try again.");
            index -= 1;
        }
    }

    index = 0;
    unsafe {
        let s_vec = arraymap.as_bytes_mut();
        for index in 0..4 {
            *s_vec.get_unchecked_mut(guesses[index]) = b' ';
        }
    }

    let is_only_spaces = arraymap.chars().all(|c| c.is_whitespace());
    if is_only_spaces {
        println!("You found all the treasures!");
        print_cow(&winning_msg_sanitized);
    } else {
        println!("You did NOT find all the treasures!");
    }
}


fn main() {
    println!("Welcome to a fun treasure hunt!");

    println!("Insert your name:");
    let mut input_string = String::new();
    match io::stdin().read_line(&mut input_string) {
        Ok(_) => {
            game(input_string.trim_end());
        },
        Err(error) => println!("Error reading input: {}", error),
    }

    println!("Goodbye!");
}

