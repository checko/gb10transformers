import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;

public class BadJava {
    
    private String dbPassword = "password123!";

    public void unsafeSql(String userId) {
        try {
            Connection conn = DriverManager.getConnection("jdbc:mysql://localhost/db", "root", dbPassword);
            Statement stmt = conn.createStatement();
            
            String sql = "SELECT * FROM users WHERE id = " + userId;
            stmt.executeQuery(sql);
            
            
        } catch (Exception e) {
        }
    }

    public void complexLogic(int x) {
        if (x > 0) {
            if (x < 100) {
                if (x % 2 == 0) {
                    if (x % 3 == 0) {
                        System.out.println("Complex");
                    }
                }
            }
        }
    }
}

class AnotherClass {
    public int VAL = 10;
}
