#ifndef KLOCKWORK_RULES_HPP
#define KLOCKWORK_RULES_HPP

#include <string>
#include <vector>
#include <map>

namespace klockwork
{

    /**
     * Severity levels for Klockwork violations
     */
    enum class Severity
    {
        CRITICAL, // Security-critical, must fix immediately
        HIGH,     // High risk, should fix ASAP
        MEDIUM,   // Medium risk, fix in next iteration
        LOW       // Low risk, nice to have
    };

    /**
     * Klockwork violation categories
     */
    enum class ViolationType
    {
        NPD_CHECK_CALL,                  // Null Pointer Dereference
        RH_LEAK,                         // Resource Leak
        SV_STRBO_BOUND_COPY,             // Buffer Overflow via String Copy
        SV_STRBO_BOUND_CAT,              // Buffer Overflow via String Concatenation
        SV_TAINTED_CALL_LOOP_BOUND,      // Tainted Loop Bound
        SV_INTOVF_ASSIGN,                // Integer Overflow on Assignment
        SV_USAGERULES_FREEING_MEMORY,    // Double Free / Use After Free
        UNINIT_STACK_MUST,               // Uninitialized Stack Variable
        SV_MISRA_COMPL_RETURN,           // Unchecked Return Value
        SV_FMT_STR_GENERIC,              // Format String Vulnerability
        SV_TAINTED_ALLOC,                // Tainted Memory Allocation Size
        SV_BANNED_FUNCTIONS,             // Use of Banned / Unsafe Functions
        SV_PASSWD_PLAINTEXT,             // Plaintext Password in Code or Log
        SV_RACE_CONDITION,               // TOCTOU Race Condition
        SV_UNSIGNED_COMPARE_ALWAYS_TRUE, // Unsigned Integer Always-True Comparison
        SV_MEMSET_WRONGSIZE,             // Incorrect memset Size Argument
        SV_ARRAY_BOUND,                  // Out-of-Bounds Array Access
        SV_SIGNAL_UNSAFE,                // Unsafe Function Called from Signal Handler
        SV_WRAP_INTEGEROVERFLOW,         // Integer Wraparound Before Size Check
        SV_INSECURE_RAND                 // Use of Cryptographically Weak RNG
    };

    /**
     * Structure to represent a single Klockwork violation
     */
    struct Violation
    {
        ViolationType type;
        Severity severity;
        std::string rule_id;
        std::string title;
        std::string description;
        std::string file_path;
        int line_number;
        std::string vulnerable_code;
        std::string fixed_code;
        std::string explanation;
        std::vector<std::string> test_cases;
    };

    /**
     * Helper functions for Klockwork analysis
     */
    class KlockworkAnalyzer
    {
    public:
        /**
         * Convert violation type to string ID
         */
        static std::string ViolationTypeToString(ViolationType type);

        /**
         * Convert violation type to title
         */
        static std::string ViolationTypeToTitle(ViolationType type);

        /**
         * Convert severity to string
         */
        static std::string SeverityToString(Severity sev);

        /**
         * Get recommended fix priority order
         */
        static std::vector<ViolationType> GetFixPriorityOrder();

        /**
         * Validate if proposed fix maintains functionality
         */
        static bool ValidateFixIntegrity(const Violation &violation);

        /**
         * Generate test case for a violation
         */
        static std::string GenerateTestCase(const Violation &violation);
    };

} // namespace klockwork

#endif // KLOCKWORK_RULES_HPP
