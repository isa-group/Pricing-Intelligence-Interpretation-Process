package org.isa.pricing.csp;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration;

@SpringBootApplication(exclude = {DataSourceAutoConfiguration.class })
public class CspApplication {

	public static void main(String[] args) {
		SpringApplication.run(CspApplication.class, args);
	}

}
