package org.isa.pricing.csp.security;

import org.chocosolver.solver.constraints.nary.nvalue.amnv.mis.F;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableWebSecurity
public class WebSecurityConfig {

    @Bean
    SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        // Disable CSRF if you're using stateless REST APIs
        http.csrf(csrf -> csrf.disable());
        
        // Allow all requests without authentication
        http.authorizeHttpRequests(auth -> auth
            .anyRequest().permitAll()
        );

        return http.build();
    }
}
